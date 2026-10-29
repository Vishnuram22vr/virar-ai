from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON, Index, Enum
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum
import uuid

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"

class EventType(str, enum.Enum):
    RUN_CREATED = "run_created"
    PLANNING = "planning"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    RETRY = "retry"
    FAILURE = "failure"
    CANCELLATION = "cancellation"
    COMPLETION = "completion"

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    correlation_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, default="VirarEngineAgent")
    agent_version = Column(String(50), nullable=False, default="1.0.0")
    execution_mode = Column(String(50), nullable=False, default="deterministic") # "deterministic" | "llm"
    status = Column(String(30), nullable=False, default=RunStatus.PENDING.value, index=True)
    
    task_input = Column(Text, nullable=False)
    final_output = Column(Text, nullable=True)
    
    # Timing & Metrics
    started_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float, nullable=True)
    
    # Provider & Tokens & Cost
    model_provider = Column(String(50), nullable=True)
    model_identifier = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    
    # Diagnostics
    error_category = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    is_demo = Column(Boolean, default=False)

    # Relationships with selectin loading to prevent lazy IO in async context
    trace_events = relationship(
        "TraceEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TraceEvent.sequence_number"
    )
    approvals = relationship(
        "ApprovalRequest",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_agent_runs_status_started", "status", "started_at"),
    )

class TraceEvent(Base):
    __tablename__ = "trace_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
    
    tool_name = Column(String(100), nullable=True, index=True)
    tool_arguments = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    
    step_duration_ms = Column(Float, nullable=True)
    status = Column(String(30), nullable=True)
    error_category = Column(String(100), nullable=True)
    error_details = Column(Text, nullable=True)
    
    metadata_payload = Column(JSON, nullable=True)
    
    run = relationship("AgentRun", back_populates="trace_events")

    __table_args__ = (
        Index("ix_trace_events_run_seq", "run_id", "sequence_number"),
    )

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)
    action_description = Column(Text, nullable=False)
    action_parameters = Column(JSON, nullable=False)
    action_fingerprint = Column(String(64), nullable=False)
    
    status = Column(String(30), nullable=False, default=ApprovalStatus.PENDING.value, index=True)
    requested_by = Column(String(100), nullable=False, default="VirarEngineAgent")
    reviewed_by = Column(String(100), nullable=True)
    decision_reason = Column(Text, nullable=True)
    
    requested_at = Column(DateTime(timezone=True), default=utc_now)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    execution_outcome = Column(Text, nullable=True)

    run = relationship("AgentRun", back_populates="approvals")

class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    test_cases_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    eval_runs = relationship("EvaluationRun", back_populates="dataset", cascade="all, delete-orphan", lazy="selectin")

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_version = Column(String(50), nullable=False)
    run_label = Column(String(100), nullable=True)
    
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    pass_rate = Column(Float, default=0.0)
    
    status = Column(String(30), default="completed")
    started_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float, default=0.0)
    
    results_detail = Column(JSON, nullable=True)

    dataset = relationship("EvaluationDataset", back_populates="eval_runs")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    action = Column(String(100), nullable=False)
    actor_id = Column(String(100), nullable=False)
    target_resource = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
