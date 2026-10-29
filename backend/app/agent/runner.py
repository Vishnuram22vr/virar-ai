import time
import asyncio
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.entities import (
    AgentRun, TraceEvent, ApprovalRequest, RunStatus, EventType, ApprovalStatus, utc_now
)
from app.tools.base import registry, ToolExecutionResult
from app.security.redaction import redact_sensitive_data
from app.security.governance import compute_parameter_fingerprint

class AgentExecutionEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._seq_counter = {}

    async def _append_event(
        self,
        run: AgentRun,
        event_type: str,
        tool_name: Optional[str] = None,
        tool_arguments: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Dict[str, Any]] = None,
        step_duration_ms: Optional[float] = None,
        status: Optional[str] = None,
        error_category: Optional[str] = None,
        error_details: Optional[str] = None,
        metadata_payload: Optional[Dict[str, Any]] = None
    ) -> TraceEvent:
        self._seq_counter[run.id] = self._seq_counter.get(run.id, 0) + 1
        seq_num = self._seq_counter[run.id]
        
        event = TraceEvent(
            run_id=run.id,
            sequence_number=seq_num,
            event_type=event_type,
            timestamp=utc_now(),
            tool_name=tool_name,
            tool_arguments=redact_sensitive_data(tool_arguments) if tool_arguments else None,
            tool_result=redact_sensitive_data(tool_result) if tool_result else None,
            step_duration_ms=step_duration_ms,
            status=status,
            error_category=error_category,
            error_details=error_details,
            metadata_payload=redact_sensitive_data(metadata_payload) if metadata_payload else None
        )
        self.session.add(event)
        await self.session.flush()
        return event

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        cost = (
            (prompt_tokens / 1000.0) * settings.COST_PER_1K_PROMPT_TOKENS +
            (completion_tokens / 1000.0) * settings.COST_PER_1K_COMPLETION_TOKENS
        )
        return round(cost, 6)

    def _parse_task_intent(self, task_input: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Deterministic task planner for offline and benchmark execution.
        Recognizes natural language queries and translates them to registered tools.
        """
        text = task_input.lower().strip()
        planned_actions = []

        # Intent: Math / Calculator
        math_match = re.search(r'(?:calculate|what is|compute|add|multiply|divide|subtract)\s+([\d\.\s\+\-\*\/\^a-z]+)', text)
        if "calculate" in text or "compute" in text or "what is" in text or any(op in text for op in ["add", "plus", "multiply", "divide", "+", "-", "*", "/"]):
            if "add" in text or "plus" in text or "+" in text:
                numbers = [float(n) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", text)]
                if len(numbers) >= 2:
                    planned_actions.append(("calculator", {"operation": "add", "a": numbers[0], "b": numbers[1]}))
            elif "subtract" in text or "minus" in text:
                numbers = [float(n) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", text)]
                if len(numbers) >= 2:
                    planned_actions.append(("calculator", {"operation": "subtract", "a": numbers[0], "b": numbers[1]}))
            elif "multiply" in text or "times" in text or "*" in text:
                numbers = [float(n) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", text)]
                if len(numbers) >= 2:
                    planned_actions.append(("calculator", {"operation": "multiply", "a": numbers[0], "b": numbers[1]}))
            elif "divide" in text or "/" in text:
                numbers = [float(n) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", text)]
                if len(numbers) >= 2:
                    planned_actions.append(("calculator", {"operation": "divide", "a": numbers[0], "b": numbers[1]}))
            elif "power" in text or "^" in text:
                numbers = [float(n) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", text)]
                if len(numbers) >= 2:
                    planned_actions.append(("calculator", {"operation": "power", "a": numbers[0], "b": numbers[1]}))

        # Intent: Service Health
        if "health" in text or "status" in text or "check service" in text:
            # Extract service name
            service_match = re.search(r'(?:service|of|for)\s+([a-zA-Z0-9_\-]+)', text)
            service_name = service_match.group(1) if service_match else "auth-service"
            if service_name in ["health", "the", "status"]:
                service_name = "auth-service"
            planned_actions.append(("service_health_lookup", {"service_name": service_name, "check_type": "ping"}))

        # Intent: Incident Ticket (Protected)
        if "incident" in text or "ticket" in text or "escalate" in text:
            sev = "high"
            if "critical" in text:
                sev = "critical"
            elif "medium" in text:
                sev = "medium"
            elif "low" in text:
                sev = "low"
            
            planned_actions.append((
                "create_incident_ticket",
                {
                    "title": f"Incident triggered by prompt: {task_input[:40]}...",
                    "severity": sev,
                    "target_service": "payment-gateway" if "payment" in text else "auth-service",
                    "description": f"Automated escalation requested based on user prompt: {task_input}"
                }
            ))

        # Direct tool call simulation if JSON format was supplied
        if text.startswith("{") and "tool" in text:
            try:
                data = json.loads(task_input)
                planned_actions.append((data.get("tool"), data.get("arguments", {})))
            except Exception:
                pass

        # Explicit detection for dangerous/unregistered command injection attempts in plain text
        if not planned_actions:
            if "bash_terminal" in text or "bash" in text and "command" in text:
                planned_actions.append(("bash_terminal", {"command": "blocked_attempt"}))
            elif "python_eval" in text or "eval" in text and ("code" in text or "python" in text):
                planned_actions.append(("python_eval", {"code": "blocked_attempt"}))
            elif "execute_shell" in text:
                planned_actions.append(("execute_shell", {"command": "blocked_attempt"}))

        return planned_actions

    async def execute_run(self, run: AgentRun) -> AgentRun:
        start_wall_time = time.perf_counter()
        run.status = RunStatus.RUNNING.value
        await self.session.commit()

        # Step 1: Trace RUN_CREATED
        await self._append_event(
            run,
            event_type=EventType.RUN_CREATED.value,
            status="success",
            metadata_payload={"agent_version": run.agent_version, "execution_mode": run.execution_mode}
        )

        # Step 2: Planning phase
        plan_start = time.perf_counter()
        planned_actions = self._parse_task_intent(run.task_input)
        plan_duration = (time.perf_counter() - plan_start) * 1000

        # Estimate prompt tokens deterministically based on character count
        prompt_tokens = max(10, len(run.task_input.split()) * 2)
        completion_tokens = 0

        await self._append_event(
            run,
            event_type=EventType.PLANNING.value,
            step_duration_ms=plan_duration,
            status="success",
            metadata_payload={
                "action_count": len(planned_actions),
                "planned_tools": [a[0] for a in planned_actions]
            }
        )

        if not planned_actions:
            # Fallback or unrecognized intent
            run.status = RunStatus.COMPLETED.value
            run.final_output = f"Virar AI processed the input: '{run.task_input}'. No external tool actions were required."
            run.duration_ms = (time.perf_counter() - start_wall_time) * 1000
            run.completed_at = utc_now()
            run.prompt_tokens = prompt_tokens
            run.completion_tokens = 15
            run.total_tokens = prompt_tokens + 15
            run.estimated_cost_usd = self._estimate_cost(run.prompt_tokens, run.completion_tokens)
            
            await self._append_event(
                run,
                event_type=EventType.COMPLETION.value,
                status="success",
                metadata_payload={"final_output": run.final_output}
            )
            await self.session.commit()
            return run

        # Execute planned actions under governance and boundary controls
        step_outputs = []
        for tool_name, args in planned_actions:
            # Check 1: Tool Allowlist
            tool = registry.get(tool_name)
            if not tool:
                error_msg = f"Security Policy Violation: Tool '{tool_name}' is not registered or allowed."
                run.status = RunStatus.FAILED.value
                run.error_category = "unregistered_tool"
                run.error_message = error_msg
                
                await self._append_event(
                    run,
                    event_type=EventType.FAILURE.value,
                    tool_name=tool_name,
                    tool_arguments=args,
                    status="failure",
                    error_category="unregistered_tool",
                    error_details=error_msg
                )
                break

            # Check 2: Governance / Approval Requirement
            if tool.requires_approval:
                # Calculate deterministic parameter fingerprint
                fp = compute_parameter_fingerprint(args)
                
                # Create Approval Request record
                approval_req = ApprovalRequest(
                    run_id=run.id,
                    tool_name=tool.name,
                    action_description=f"Requesting execution of protected tool '{tool.name}'",
                    action_parameters=args,
                    action_fingerprint=fp,
                    status=ApprovalStatus.PENDING.value,
                    requested_by=run.agent_name
                )
                self.session.add(approval_req)
                
                run.status = RunStatus.WAITING_APPROVAL.value
                await self._append_event(
                    run,
                    event_type=EventType.APPROVAL_REQUESTED.value,
                    tool_name=tool.name,
                    tool_arguments=args,
                    status="pending",
                    metadata_payload={
                        "approval_request_id": approval_req.id,
                        "fingerprint": fp,
                        "governance_rule": "Protected actions require explicit authenticated human sign-off."
                    }
                )
                run.final_output = f"Execution paused. Action '{tool.name}' requires human approval before proceeding."
                await self.session.commit()
                return run

            # Step 3: Invoke Tool (Normal execution)
            await self._append_event(
                run,
                event_type=EventType.TOOL_CALL.value,
                tool_name=tool.name,
                tool_arguments=args,
                status="invoked"
            )

            tool_result: ToolExecutionResult
            try:
                # Validate and execute
                tool_result = await tool.execute(args)
            except Exception as e:
                tool_result = ToolExecutionResult(
                    success=False,
                    error=str(e),
                    error_category="validation_or_runtime_exception",
                    duration_ms=1.0
                )

            # Record tool result trace
            await self._append_event(
                run,
                event_type=EventType.TOOL_RESULT.value,
                tool_name=tool.name,
                tool_arguments=args,
                tool_result=tool_result.data if tool_result.success else None,
                step_duration_ms=tool_result.duration_ms,
                status="success" if tool_result.success else "failure",
                error_category=tool_result.error_category,
                error_details=tool_result.error
            )

            if not tool_result.success:
                run.status = RunStatus.FAILED.value
                run.error_category = tool_result.error_category or "tool_execution_failed"
                run.error_message = tool_result.error
                await self._append_event(
                    run,
                    event_type=EventType.FAILURE.value,
                    tool_name=tool.name,
                    status="failure",
                    error_category=run.error_category,
                    error_details=run.error_message
                )
                break
            else:
                step_outputs.append({tool.name: tool_result.data})

        # Finalize run metrics
        if run.status != RunStatus.FAILED.value:
            run.status = RunStatus.COMPLETED.value
            run.final_output = f"Successfully executed {len(step_outputs)} actions. Results: {step_outputs}"
            await self._append_event(
                run,
                event_type=EventType.COMPLETION.value,
                status="success",
                metadata_payload={"summary": run.final_output}
            )

        run.completed_at = utc_now()
        run.duration_ms = (time.perf_counter() - start_wall_time) * 1000
        run.prompt_tokens = prompt_tokens
        run.completion_tokens = 45 if run.status == RunStatus.COMPLETED.value else 20
        run.total_tokens = run.prompt_tokens + run.completion_tokens
        run.estimated_cost_usd = self._estimate_cost(run.prompt_tokens, run.completion_tokens)
        run.model_provider = settings.LLM_PROVIDER
        run.model_identifier = settings.LLM_MODEL
        
        await self.session.commit()
        return run

    async def execute_approved_action(self, approval_id: str, reviewer_id: str, decision: str, reason: Optional[str] = None) -> ApprovalRequest:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        result = await self.session.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            raise ValueError(f"Approval request '{approval_id}' not found.")
        
        if req.status != ApprovalStatus.PENDING.value:
            raise ValueError(f"Approval request is already in '{req.status}' state.")

        req.reviewed_by = reviewer_id
        req.decision_reason = reason
        req.decided_at = utc_now()

        # Load run
        run_stmt = select(AgentRun).where(AgentRun.id == req.run_id)
        run_res = await self.session.execute(run_stmt)
        run = run_res.scalar_one_or_none()

        if decision == "rejected":
            req.status = ApprovalStatus.REJECTED.value
            req.execution_outcome = "Action rejected by human reviewer. Execution blocked."
            if run:
                run.status = RunStatus.FAILED.value
                run.error_category = "approval_rejected"
                run.error_message = f"Action '{req.tool_name}' was rejected by reviewer '{reviewer_id}': {reason or 'No reason provided'}"
                await self._append_event(
                    run,
                    event_type=EventType.APPROVAL_DECIDED.value,
                    tool_name=req.tool_name,
                    status="rejected",
                    metadata_payload={"reviewer": reviewer_id, "reason": reason}
                )
                await self._append_event(
                    run,
                    event_type=EventType.FAILURE.value,
                    tool_name=req.tool_name,
                    status="failure",
                    error_category="approval_rejected",
                    error_details=run.error_message
                )
            await self.session.commit()
            return req

        # Decision is APPROVED
        # Security Verification: Recompute and check fingerprint to prevent parameter tampering
        current_fp = compute_parameter_fingerprint(req.action_parameters)
        if current_fp != req.action_fingerprint:
            req.status = ApprovalStatus.CANCELLED.value
            req.execution_outcome = "Integrity check failed: action parameters were tampered with!"
            if run:
                run.status = RunStatus.FAILED.value
                run.error_category = "tamper_detected"
                run.error_message = "Integrity check failure: action parameters changed after approval request."
            await self.session.commit()
            return req

        req.status = ApprovalStatus.APPROVED.value
        tool = registry.get(req.tool_name)
        if not tool:
            req.execution_outcome = f"Error: Tool '{req.tool_name}' not available at execution time."
            if run:
                run.status = RunStatus.FAILED.value
            await self.session.commit()
            return req

        # Record approval decision event
        if run:
            await self._append_event(
                run,
                event_type=EventType.APPROVAL_DECIDED.value,
                tool_name=req.tool_name,
                status="approved",
                metadata_payload={"reviewer": reviewer_id, "reason": reason}
            )

        # Execute approved tool
        tool_res = await tool.execute(req.action_parameters)
        req.execution_outcome = json.dumps(tool_res.data if tool_res.success else {"error": tool_res.error})

        if run:
            await self._append_event(
                run,
                event_type=EventType.TOOL_RESULT.value,
                tool_name=tool.name,
                tool_arguments=req.action_parameters,
                tool_result=tool_res.data if tool_res.success else None,
                step_duration_ms=tool_res.duration_ms,
                status="success" if tool_res.success else "failure",
                error_category=tool_res.error_category,
                error_details=tool_res.error
            )
            if tool_res.success:
                run.status = RunStatus.COMPLETED.value
                run.final_output = f"Approved action completed successfully: {tool_res.data}"
                await self._append_event(
                    run,
                    event_type=EventType.COMPLETION.value,
                    status="success",
                    metadata_payload={"final_output": run.final_output}
                )
            else:
                run.status = RunStatus.FAILED.value
                run.error_category = tool_res.error_category
                run.error_message = tool_res.error

        await self.session.commit()
        return req
