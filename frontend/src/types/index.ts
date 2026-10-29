export interface AgentRun {
  id: string;
  correlation_id: string;
  agent_name: string;
  agent_version: string;
  execution_mode: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'waiting_approval';
  task_input: string;
  final_output: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  model_provider: string | null;
  model_identifier: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  error_category: string | null;
  error_message: string | null;
  idempotency_key: string | null;
  is_demo: boolean;
  trace_events?: TraceEvent[];
}

export interface TraceEvent {
  id: string;
  run_id: string;
  sequence_number: number;
  event_type: string;
  timestamp: string;
  tool_name: string | null;
  tool_arguments: Record<string, any> | null;
  tool_result: Record<string, any> | null;
  step_duration_ms: number | null;
  status: string | null;
  error_category: string | null;
  error_details: string | null;
  metadata_payload: Record<string, any> | null;
}

export interface ApprovalRequest {
  id: string;
  run_id: string;
  tool_name: string;
  action_description: string;
  action_parameters: Record<string, any>;
  action_fingerprint: string;
  status: 'pending' | 'approved' | 'rejected' | 'cancelled' | 'expired';
  requested_by: string;
  reviewed_by: string | null;
  decision_reason: string | null;
  requested_at: string;
  decided_at: string | null;
  execution_outcome: string | null;
}

export interface ToolMetadata {
  name: string;
  description: string;
  requires_approval: boolean;
  permission_level: string;
  input_schema: Record<string, any>;
}

export interface EvaluationRun {
  id: string;
  dataset_id: string;
  agent_version: string;
  run_label: string | null;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number;
  results_detail: Array<{
    case_id: string;
    category: string;
    description: string;
    input: string;
    passed: boolean;
    diagnosis: string;
    actual_status: string;
    actual_error_category: string | null;
    run_id: string;
    duration_ms: number | null;
  }>;
}

export interface DashboardMetrics {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  waiting_approval_runs: number;
  success_rate: number;
  avg_latency_ms: number;
  total_estimated_cost_usd: number;
  total_tokens: number;
  active_eval_pass_rate: number;
  recent_failures: Array<{
    id: string;
    task_input: string;
    error_category: string | null;
    error_message: string | null;
    started_at: string;
  }>;
}
