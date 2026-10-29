const API_BASE = '/api/v1';

export async function fetchMetrics(): Promise<any> {
  const res = await fetch(`${API_BASE}/metrics/dashboard`);
  if (!res.ok) throw new Error('Failed to load dashboard metrics');
  return res.json();
}

export async function fetchRuns(status?: string): Promise<any> {
  const url = status ? `${API_BASE}/runs?status=${status}` : `${API_BASE}/runs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch runs');
  return res.json();
}

export async function fetchRunTraces(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/runs/${runId}/traces`);
  if (!res.ok) throw new Error('Failed to fetch run traces');
  return res.json();
}

export async function createRun(taskInput: string, executionMode = 'deterministic'): Promise<any> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_input: taskInput, execution_mode: executionMode })
  });
  if (!res.ok) throw new Error('Failed to create agent run');
  return res.json();
}

export async function fetchTools(): Promise<any> {
  const res = await fetch(`${API_BASE}/tools`);
  if (!res.ok) throw new Error('Failed to fetch tools');
  return res.json();
}

export async function fetchApprovals(status?: string): Promise<any> {
  const url = status ? `${API_BASE}/approvals?status=${status}` : `${API_BASE}/approvals`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch approvals');
  return res.json();
}

export async function decideApproval(approvalId: string, decision: 'approved' | 'rejected', reason?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}/decide`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': 'human-reviewer-admin'
    },
    body: JSON.stringify({ decision, reason })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to submit approval decision');
  }
  return res.json();
}

export async function fetchEvalRuns(): Promise<any> {
  const res = await fetch(`${API_BASE}/evaluations/runs`);
  if (!res.ok) throw new Error('Failed to fetch evaluation runs');
  return res.json();
}

export async function triggerEvalRun(agentVersion = '1.0.0'): Promise<any> {
  const res = await fetch(`${API_BASE}/evaluations/run?dataset_name=core_suite_v1&agent_version=${agentVersion}`, {
    method: 'POST',
    headers: { 'X-User-Id': 'qa-engineer' }
  });
  if (!res.ok) throw new Error('Failed to trigger evaluation run');
  return res.json();
}

export async function seedDemoData(): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/seed`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to seed demo data');
  return res.json();
}
