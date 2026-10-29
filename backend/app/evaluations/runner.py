import json
import time
import uuid
import os
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entities import EvaluationDataset, EvaluationRun, AgentRun, RunStatus, utc_now
from app.agent.runner import AgentExecutionEngine

class EvaluationRunner:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_engine = AgentExecutionEngine(session)

    async def ensure_default_dataset(self) -> EvaluationDataset:
        stmt = select(EvaluationDataset).where(EvaluationDataset.name == "core_suite_v1")
        res = await self.session.execute(stmt)
        dataset = res.scalar_one_or_none()
        
        dataset_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "evals", "datasets", "core_suite_v1.json"
        )
        normalized_path = os.path.normpath(dataset_path)

        if not os.path.exists(normalized_path):
            test_cases_count = 20
        else:
            with open(normalized_path, "r", encoding="utf-8") as f:
                cases = json.load(f)
                test_cases_count = len(cases)

        if not dataset:
            dataset = EvaluationDataset(
                name="core_suite_v1",
                description="Core 20 deterministic evaluation benchmarks testing normal behavior, arithmetic boundaries, service health lookups, unknown tools, and governance approvals.",
                version="1.0.0",
                test_cases_count=test_cases_count
            )
            self.session.add(dataset)
            await self.session.commit()
            await self.session.refresh(dataset)
            
        return dataset

    async def run_evaluation_suite(
        self,
        dataset_name: str = "core_suite_v1",
        agent_version: str = "1.0.0",
        run_label: Optional[str] = None
    ) -> EvaluationRun:
        dataset = await self.ensure_default_dataset()
        
        # Load test cases
        dataset_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals", "datasets", f"{dataset_name}.json")
        )
        
        with open(dataset_path, "r", encoding="utf-8") as f:
            cases: List[Dict[str, Any]] = json.load(f)

        start_time = time.perf_counter()
        results_detail = []
        passed_count = 0

        for case in cases:
            case_id = case.get("id")
            input_text = case.get("input")
            expected_status = case.get("expected_status")
            expected_error = case.get("expected_error_category")
            expected_result = case.get("expected_result")

            # Create an isolated agent run for this eval case
            eval_run = AgentRun(
                correlation_id=str(uuid.uuid4()),
                agent_name="VirarEvaluationAgent",
                agent_version=agent_version,
                execution_mode="deterministic",
                task_input=input_text,
                is_demo=False
            )
            self.session.add(eval_run)
            await self.session.flush()

            # Execute via Engine
            await self.agent_engine.execute_run(eval_run)

            # Evaluate assertions
            passed = True
            diagnosis = []

            # Assertion 1: Status
            if eval_run.status != expected_status:
                passed = False
                diagnosis.append(f"Status mismatch: expected '{expected_status}', got '{eval_run.status}'")

            # Assertion 2: Error Category (if expected)
            if expected_error and eval_run.error_category != expected_error:
                passed = False
                diagnosis.append(f"Error category mismatch: expected '{expected_error}', got '{eval_run.error_category}'")

            if passed:
                passed_count += 1

            results_detail.append({
                "case_id": case_id,
                "category": case.get("category"),
                "description": case.get("description"),
                "input": input_text,
                "passed": passed,
                "diagnosis": "; ".join(diagnosis) if diagnosis else "Passed all deterministic checks.",
                "actual_status": eval_run.status,
                "actual_error_category": eval_run.error_category,
                "run_id": eval_run.id,
                "duration_ms": eval_run.duration_ms
            })

        total_cases = len(cases)
        pass_rate = round((passed_count / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
        duration_ms = (time.perf_counter() - start_time) * 1000

        eval_run_record = EvaluationRun(
            dataset_id=dataset.id,
            agent_version=agent_version,
            run_label=run_label or f"Eval Run {time.strftime('%Y-%m-%d %H:%M:%S')}",
            total_cases=total_cases,
            passed_cases=passed_count,
            failed_cases=total_cases - passed_count,
            pass_rate=pass_rate,
            status="completed",
            completed_at=utc_now(),
            duration_ms=duration_ms,
            results_detail=results_detail
        )

        self.session.add(eval_run_record)
        await self.session.commit()
        await self.session.refresh(eval_run_record)
        return eval_run_record
