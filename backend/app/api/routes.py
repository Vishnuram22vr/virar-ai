import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.entities import AgentRun, TraceEvent, ApprovalRequest, EvaluationDataset, EvaluationRun, RunStatus
from app.schemas.api import (
    AgentRunCreate, AgentRunResponse, TraceEventResponse,
    ApprovalResponse, ApprovalDecisionRequest, ToolMetadataResponse, DashboardMetricsResponse
)
from app.agent.runner import AgentExecutionEngine
from app.tools.base import registry
from app.evaluations.runner import EvaluationRunner
from app.security.governance import get_current_user, DevUser, enforce_not_self_approval

router = APIRouter()

# --- Health Endpoints ---
@router.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "Virar AI Observability Platform", "version": "1.0.0"}

@router.get("/ready", tags=["System"])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        # Check DB connection
        await db.execute(select(func.count(AgentRun.id)))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database readiness check failed: {str(e)}")

# --- Agent Runs ---
@router.post("/runs", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED, tags=["Agent Runs"])
async def create_agent_run(
    payload: AgentRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: DevUser = Depends(get_current_user)
):
    # Idempotency check if key is provided
    if payload.idempotency_key:
        stmt = select(AgentRun).where(AgentRun.idempotency_key == payload.idempotency_key)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            # Return existing idempotent run
            return existing

    new_run = AgentRun(
        correlation_id=str(uuid.uuid4()),
        agent_name="VirarEngineAgent",
        agent_version="1.0.0",
        execution_mode=payload.execution_mode or "deterministic",
        task_input=payload.task_input,
        idempotency_key=payload.idempotency_key,
        is_demo=payload.is_demo or False
    )
    db.add(new_run)
    await db.commit()
    await db.refresh(new_run)

    # Execute run
    engine = AgentExecutionEngine(db)
    executed_run = await engine.execute_run(new_run)
    
    # Reload with traces
    stmt = select(AgentRun).where(AgentRun.id == executed_run.id)
    res = await db.execute(stmt)
    return res.scalar_one()

@router.get("/runs", response_model=List[AgentRunResponse], tags=["Agent Runs"])
async def list_agent_runs(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AgentRun).order_by(desc(AgentRun.started_at)).limit(limit).offset(offset)
    if status_filter:
        stmt = stmt.where(AgentRun.status == status_filter)
    
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/runs/{run_id}", response_model=AgentRunResponse, tags=["Agent Runs"])
async def get_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AgentRun).where(AgentRun.id == run_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run

@router.get("/runs/{run_id}/traces", response_model=List[TraceEventResponse], tags=["Agent Runs"])
async def get_run_traces(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TraceEvent).where(TraceEvent.run_id == run_id).order_by(TraceEvent.sequence_number)
    res = await db.execute(stmt)
    return res.scalars().all()

# --- Tools and Policies ---
@router.get("/tools", response_model=List[ToolMetadataResponse], tags=["Tools & Policies"])
async def list_tools():
    return registry.get_tool_metadata_list()

# --- Approvals and Governance ---
@router.get("/approvals", response_model=List[ApprovalResponse], tags=["Approvals"])
async def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ApprovalRequest).order_by(desc(ApprovalRequest.requested_at))
    if status_filter:
        stmt = stmt.where(ApprovalRequest.status == status_filter)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/approvals/{approval_id}/decide", response_model=ApprovalResponse, tags=["Approvals"])
async def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DevUser = Depends(get_current_user)
):
    # Verify approval exists
    stmt = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    # Governance rule: Requesting agent/actor cannot approve its own action
    enforce_not_self_approval(req.requested_by, current_user.user_id)

    engine = AgentExecutionEngine(db)
    try:
        updated_req = await engine.execute_approved_action(
            approval_id=approval_id,
            reviewer_id=current_user.user_id,
            decision=payload.decision,
            reason=payload.reason
        )
        return updated_req
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Evaluations ---
@router.get("/evaluations/datasets", tags=["Evaluations"])
async def list_evaluation_datasets(db: AsyncSession = Depends(get_db)):
    eval_runner = EvaluationRunner(db)
    await eval_runner.ensure_default_dataset()
    stmt = select(EvaluationDataset)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/evaluations/run", tags=["Evaluations"])
async def trigger_evaluation_run(
    dataset_name: str = Query("core_suite_v1"),
    agent_version: str = Query("1.0.0"),
    db: AsyncSession = Depends(get_db),
    current_user: DevUser = Depends(get_current_user)
):
    eval_runner = EvaluationRunner(db)
    eval_run = await eval_runner.run_evaluation_suite(
        dataset_name=dataset_name,
        agent_version=agent_version
    )
    return eval_run

@router.get("/evaluations/runs", tags=["Evaluations"])
async def list_evaluation_runs(db: AsyncSession = Depends(get_db)):
    stmt = select(EvaluationRun).order_by(desc(EvaluationRun.started_at))
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/evaluations/compare", tags=["Evaluations"])
async def compare_evaluation_runs(
    run_id_a: str = Query(...),
    run_id_b: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(EvaluationRun).where(EvaluationRun.id.in_([run_id_a, run_id_b]))
    res = await db.execute(stmt)
    runs = {r.id: r for r in res.scalars().all()}
    
    if run_id_a not in runs or run_id_b not in runs:
        raise HTTPException(status_code=404, detail="One or both evaluation runs not found for comparison.")

    run_a = runs[run_id_a]
    run_b = runs[run_id_b]

    diff = {
        "run_a": {
            "id": run_a.id, "version": run_a.agent_version, "pass_rate": run_a.pass_rate,
            "passed": run_a.passed_cases, "failed": run_a.failed_cases, "duration_ms": run_a.duration_ms
        },
        "run_b": {
            "id": run_b.id, "version": run_b.agent_version, "pass_rate": run_b.pass_rate,
            "passed": run_b.passed_cases, "failed": run_b.failed_cases, "duration_ms": run_b.duration_ms
        },
        "pass_rate_delta": round(run_b.pass_rate - run_a.pass_rate, 2),
        "is_regression": (run_b.pass_rate < run_a.pass_rate)
    }
    return diff

# --- Dashboard Metrics ---
@router.get("/metrics/dashboard", response_model=DashboardMetricsResponse, tags=["Dashboard"])
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    # Total runs
    total_res = await db.execute(select(func.count(AgentRun.id)))
    total_runs = total_res.scalar() or 0

    succ_res = await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status == RunStatus.COMPLETED.value))
    successful_runs = succ_res.scalar() or 0

    fail_res = await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status == RunStatus.FAILED.value))
    failed_runs = fail_res.scalar() or 0

    waiting_res = await db.execute(select(func.count(AgentRun.id)).where(AgentRun.status == RunStatus.WAITING_APPROVAL.value))
    waiting_approval_runs = waiting_res.scalar() or 0

    success_rate = round((successful_runs / total_runs * 100.0), 2) if total_runs > 0 else 0.0

    avg_lat_res = await db.execute(select(func.avg(AgentRun.duration_ms)).where(AgentRun.duration_ms.isnot(None)))
    avg_latency = round(avg_lat_res.scalar() or 0.0, 2)

    cost_res = await db.execute(select(func.sum(AgentRun.estimated_cost_usd)))
    total_cost = round(cost_res.scalar() or 0.0, 6)

    token_res = await db.execute(select(func.sum(AgentRun.total_tokens)))
    total_tokens = token_res.scalar() or 0

    # Latest eval pass rate
    latest_eval_res = await db.execute(select(EvaluationRun).order_by(desc(EvaluationRun.started_at)).limit(1))
    latest_eval = latest_eval_res.scalar_one_or_none()
    active_eval_pass_rate = latest_eval.pass_rate if latest_eval else 0.0

    # Recent failures
    fail_stmt = select(AgentRun).where(AgentRun.status == RunStatus.FAILED.value).order_by(desc(AgentRun.started_at)).limit(5)
    fail_rows = await db.execute(fail_stmt)
    recent_failures = [
        {
            "id": r.id,
            "task_input": r.task_input,
            "error_category": r.error_category,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None
        }
        for r in fail_rows.scalars().all()
    ]

    return DashboardMetricsResponse(
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        waiting_approval_runs=waiting_approval_runs,
        success_rate=success_rate,
        avg_latency_ms=avg_latency,
        total_estimated_cost_usd=total_cost,
        total_tokens=total_tokens,
        active_eval_pass_rate=active_eval_pass_rate,
        recent_failures=recent_failures
    )

# --- Demo Seeding Endpoint ---
@router.post("/demo/seed", tags=["System"])
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    eval_runner = EvaluationRunner(db)
    await eval_runner.ensure_default_dataset()
    
    # Run an initial evaluation suite to have real evaluation metrics
    eval_run = await eval_runner.run_evaluation_suite(agent_version="1.0.0", run_label="Baseline Release v1.0.0")

    # Run sample agent tasks
    engine = AgentExecutionEngine(db)
    sample_inputs = [
        ("Calculate multiply 45 and 18", False),
        ("Check health of payment-gateway", False),
        ("Create an incident ticket for database downtime", False)
    ]
    for prompt, is_demo in sample_inputs:
        run = AgentRun(
            correlation_id=str(uuid.uuid4()),
            agent_name="VirarEngineAgent",
            agent_version="1.0.0",
            execution_mode="deterministic",
            task_input=prompt,
            is_demo=True
        )
        db.add(run)
        await db.commit()
        await engine.execute_run(run)

    return {"message": "Demo data and baseline evaluations successfully seeded."}
