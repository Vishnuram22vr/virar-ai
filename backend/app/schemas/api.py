from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class AgentRunCreate(BaseModel):
    task_input: str = Field(..., min_length=1, description="Prompt or goal for the agent to execute")
    execution_mode: Optional[str] = Field("deterministic", description="'deterministic' or 'llm'")
    idempotency_key: Optional[str] = Field(None, description="Optional key to ensure idempotent run creation")
    is_demo: Optional[bool] = False

class TraceEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    sequence_number: int
    event_type: str
    timestamp: datetime
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    step_duration_ms: Optional[float] = None
    status: Optional[str] = None
    error_category: Optional[str] = None
    error_details: Optional[str] = None
    metadata_payload: Optional[Dict[str, Any]] = None

class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    correlation_id: str
    agent_name: str
    agent_version: str
    execution_mode: str
    status: str
    task_input: str
    final_output: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    model_provider: Optional[str] = None
    model_identifier: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    idempotency_key: Optional[str] = None
    is_demo: bool
    trace_events: Optional[List[TraceEventResponse]] = None

class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="'approved' or 'rejected'")
    reason: Optional[str] = Field(None, description="Reason for decision")

class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    tool_name: str
    action_description: str
    action_parameters: Dict[str, Any]
    action_fingerprint: str
    status: str
    requested_by: str
    reviewed_by: Optional[str] = None
    decision_reason: Optional[str] = None
    requested_at: datetime
    decided_at: Optional[datetime] = None
    execution_outcome: Optional[str] = None

class ToolMetadataResponse(BaseModel):
    name: str
    description: str
    requires_approval: bool
    permission_level: str
    input_schema: Dict[str, Any]

class DashboardMetricsResponse(BaseModel):
    total_runs: int
    successful_runs: int
    failed_runs: int
    waiting_approval_runs: int
    success_rate: float
    avg_latency_ms: float
    total_estimated_cost_usd: float
    total_tokens: int
    active_eval_pass_rate: float
    recent_failures: List[Dict[str, Any]]
