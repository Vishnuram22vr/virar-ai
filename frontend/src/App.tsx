import React, { useState, useEffect } from 'react';
import { 
  Activity, Play, CheckCircle2, ShieldCheck, 
  Settings as SettingsIcon, Terminal, RefreshCw, Cpu, Database
} from 'lucide-react';
import { 
  fetchMetrics, fetchRuns, fetchRunTraces, createRun, fetchTools, 
  fetchApprovals, decideApproval, fetchEvalRuns, triggerEvalRun, seedDemoData 
} from './api/client';
import { AgentRun, TraceEvent, ApprovalRequest, ToolMetadata, EvaluationRun, DashboardMetrics } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'runs' | 'evals' | 'tools' | 'approvals' | 'settings'>('overview');
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);
  const [runTraces, setRunTraces] = useState<TraceEvent[]>([]);
  const [tools, setTools] = useState<ToolMetadata[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [evalRuns, setEvalRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskInput, setTaskInput] = useState('');
  const [notification, setNotification] = useState<string | null>(null);

  // Load Initial Data
  const refreshAll = async () => {
    setLoading(true);
    try {
      const [m, r, t, a, e] = await Promise.all([
        fetchMetrics().catch(() => null),
        fetchRuns().catch(() => []),
        fetchTools().catch(() => []),
        fetchApprovals().catch(() => []),
        fetchEvalRuns().catch(() => [])
      ]);
      setMetrics(m);
      setRuns(r);
      setTools(t);
      setApprovals(a);
      setEvalRuns(e);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  const handleCreateRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInput.trim()) return;
    setLoading(true);
    try {
      const newRun = await createRun(taskInput);
      setTaskInput('');
      showNotification(`Run #${newRun.id.slice(0, 8)} started!`);
      await refreshAll();
      setSelectedRun(newRun);
      const traces = await fetchRunTraces(newRun.id);
      setRunTraces(traces);
      setActiveTab('runs');
    } catch (err: any) {
      alert(`Error starting run: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRun = async (run: AgentRun) => {
    setSelectedRun(run);
    try {
      const traces = await fetchRunTraces(run.id);
      setRunTraces(traces);
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleApprovalDecision = async (id: string, decision: 'approved' | 'rejected') => {
    setLoading(true);
    try {
      await decideApproval(id, decision, `Action ${decision} via Virar AI Governance Portal`);
      showNotification(`Approval #${id.slice(0, 8)} marked as ${decision}.`);
      await refreshAll();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerEval = async () => {
    setLoading(true);
    try {
      showNotification('Running deterministic 20-case evaluation suite...');
      const evalResult = await triggerEvalRun('1.0.0');
      showNotification(`Evaluation complete! Pass rate: ${evalResult.pass_rate}%`);
      await refreshAll();
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSeedDemo = async () => {
    setLoading(true);
    try {
      await seedDemoData();
      showNotification('Demo data and baseline evaluation benchmarks seeded!');
      await refreshAll();
    } catch (err: any) {
      alert(`Failed to seed demo data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <Activity size={28} color="#60a5fa" />
          <div>
            <div className="brand-title">Virar AI</div>
            <div className="brand-subtitle">Agent Observability Platform</div>
          </div>
        </div>

        <nav className="nav-links">
          <button 
            className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Activity size={18} /> Overview
          </button>
          <button 
            className={`nav-item ${activeTab === 'runs' ? 'active' : ''}`}
            onClick={() => setActiveTab('runs')}
          >
            <Terminal size={18} /> Agent Runs ({runs.length})
          </button>
          <button 
            className={`nav-item ${activeTab === 'evals' ? 'active' : ''}`}
            onClick={() => setActiveTab('evals')}
          >
            <CheckCircle2 size={18} /> Evaluations ({evalRuns.length})
          </button>
          <button 
            className={`nav-item ${activeTab === 'tools' ? 'active' : ''}`}
            onClick={() => setActiveTab('tools')}
          >
            <Cpu size={18} /> Tools & Policies ({tools.length})
          </button>
          <button 
            className={`nav-item ${activeTab === 'approvals' ? 'active' : ''}`}
            onClick={() => setActiveTab('approvals')}
          >
            <ShieldCheck size={18} /> Approvals ({approvals.filter(a => a.status === 'pending').length})
          </button>
          <button 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <SettingsIcon size={18} /> Settings & Docs
          </button>
        </nav>

        <div style={{ marginTop: 'auto', borderTop: '1px solid #233154', paddingTop: '16px' }}>
          <button className="btn btn-secondary" style={{ width: '100%' }} onClick={handleSeedDemo}>
            <Database size={16} /> Seed Demo Data
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="content-area">
        {notification && (
          <div style={{ 
            background: '#1e293b', 
            border: '1px solid #3b82f6', 
            color: '#60a5fa', 
            padding: '12px 18px', 
            borderRadius: '8px', 
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <CheckCircle2 size={18} /> {notification}
          </div>
        )}

        {/* Tab A: Overview */}
        {activeTab === 'overview' && (
          <div>
            <div className="page-header">
              <div>
                <h1 className="page-title">Platform Overview</h1>
                <p className="page-desc">Production observability metrics, latency, token spend, and reliability telemetry.</p>
              </div>
              <button className="btn btn-secondary" onClick={refreshAll}>
                <RefreshCw size={16} /> Refresh
              </button>
            </div>

            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Total Executions</div>
                <div className="stat-value">{metrics?.total_runs ?? 0}</div>
                <div className="stat-subtext">{metrics?.waiting_approval_runs ?? 0} pending approvals</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Success Rate</div>
                <div className="stat-value">{metrics?.success_rate ?? 0}%</div>
                <div className="stat-subtext">{metrics?.successful_runs ?? 0} passed / {metrics?.failed_runs ?? 0} failed</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Average Latency</div>
                <div className="stat-value">{metrics?.avg_latency_ms ?? 0} ms</div>
                <div className="stat-subtext">Step execution duration</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Active Eval Pass Rate</div>
                <div className="stat-value">{metrics?.active_eval_pass_rate ?? 0}%</div>
                <div className="stat-subtext">Core 20-case suite</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Estimated Cost</div>
                <div className="stat-value">${metrics?.total_estimated_cost_usd?.toFixed(5) ?? '0.00000'}</div>
                <div className="stat-subtext">{metrics?.total_tokens ?? 0} total tokens</div>
              </div>
            </div>

            {/* Quick Dispatch Agent Task */}
            <div className="card">
              <div className="card-title">
                <span>Dispatch Agent Task</span>
                <span className="badge badge-info">Deterministic Mode</span>
              </div>
              <form onSubmit={handleCreateRun}>
                <input 
                  type="text" 
                  className="input-box" 
                  placeholder="e.g. 'Calculate multiply 24 and 5', 'Check health of payment-gateway', or 'Create incident for database outage'" 
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                />
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  <Play size={16} /> Run Agent Task
                </button>
              </form>
            </div>

            {/* Recent Failures & Reliability */}
            <div className="card">
              <div className="card-title">
                <span>Recent Failures & Root Cause Diagnostics</span>
                <span className="badge badge-danger">{metrics?.recent_failures?.length ?? 0} Failures</span>
              </div>
              {metrics?.recent_failures && metrics.recent_failures.length > 0 ? (
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Task Input</th>
                      <th>Error Category</th>
                      <th>Safe Diagnostic Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.recent_failures.map((f) => (
                      <tr key={f.id}>
                        <td>{new Date(f.started_at).toLocaleTimeString()}</td>
                        <td style={{ fontWeight: 500 }}>{f.task_input}</td>
                        <td><span className="badge badge-danger">{f.error_category || 'general'}</span></td>
                        <td style={{ color: '#ef4444' }}>{f.error_message || 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>No failures recorded. All agent runs succeeded!</p>
              )}
            </div>
          </div>
        )}

        {/* Tab B: Agent Runs */}
        {activeTab === 'runs' && (
          <div>
            <div className="page-header">
              <div>
                <h1 className="page-title">Agent Execution Traces</h1>
                <p className="page-desc">Chronological trace spans, validated tool parameters, duration, and error diagnostics.</p>
              </div>
              <button className="btn btn-secondary" onClick={refreshAll}>
                <RefreshCw size={16} /> Refresh
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: selectedRun ? '1fr 1fr' : '1fr', gap: '24px' }}>
              <div className="card">
                <div className="card-title">Execution Runs ({runs.length})</div>
                <table>
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Task Prompt</th>
                      <th>Duration</th>
                      <th>Tokens</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr key={r.id} style={{ cursor: 'pointer' }} onClick={() => handleSelectRun(r)}>
                        <td>
                          <span className={`badge ${
                            r.status === 'completed' ? 'badge-success' : 
                            r.status === 'failed' ? 'badge-danger' : 
                            r.status === 'waiting_approval' ? 'badge-warning' : 'badge-info'
                          }`}>
                            {r.status}
                          </span>
                        </td>
                        <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {r.task_input}
                        </td>
                        <td>{r.duration_ms ? `${Math.round(r.duration_ms)} ms` : '-'}</td>
                        <td>{r.total_tokens}</td>
                        <td>
                          <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleSelectRun(r)}>
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {selectedRun && (
                <div className="card">
                  <div className="card-title">
                    <span>Trace Detail: #{selectedRun.id.slice(0, 8)}</span>
                    <button className="btn btn-secondary" style={{ padding: '4px 8px' }} onClick={() => setSelectedRun(null)}>Close</button>
                  </div>
                  <div style={{ marginBottom: '16px', fontSize: '0.875rem' }}>
                    <p><strong>Goal:</strong> {selectedRun.task_input}</p>
                    <p><strong>Agent Version:</strong> {selectedRun.agent_version} | <strong>Mode:</strong> {selectedRun.execution_mode}</p>
                    <p><strong>Status:</strong> <span className="badge badge-info">{selectedRun.status}</span></p>
                    {selectedRun.final_output && <p><strong>Result:</strong> {selectedRun.final_output}</p>}
                    {selectedRun.error_message && <p style={{ color: '#ef4444' }}><strong>Error:</strong> {selectedRun.error_message}</p>}
                  </div>

                  <h4 style={{ fontSize: '0.95rem', marginBottom: '8px' }}>Execution Trace Spans ({runTraces.length})</h4>
                  <div className="trace-timeline">
                    {runTraces.map((t) => (
                      <div key={t.id} className="trace-step">
                        <div className="trace-header">
                          <span className="badge badge-purple">{t.event_type}</span>
                          <span>{t.tool_name ? `Tool: ${t.tool_name}` : ''}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: 'auto' }}>
                            {t.step_duration_ms ? `${t.step_duration_ms.toFixed(1)}ms` : ''}
                          </span>
                        </div>
                        {(t.tool_arguments || t.tool_result || t.metadata_payload || t.error_details) && (
                          <div className="trace-body">
                            {t.tool_arguments && <div><strong>Args:</strong> {JSON.stringify(t.tool_arguments)}</div>}
                            {t.tool_result && <div><strong>Result:</strong> {JSON.stringify(t.tool_result)}</div>}
                            {t.error_details && <div style={{ color: '#ef4444' }}><strong>Error:</strong> {t.error_details}</div>}
                            {t.metadata_payload && <div><strong>Metadata:</strong> {JSON.stringify(t.metadata_payload)}</div>}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab C: Evaluations */}
        {activeTab === 'evals' && (
          <div>
            <div className="page-header">
              <div>
                <h1 className="page-title">Deterministic Evaluations</h1>
                <p className="page-desc">20-case test suite verifying normal behavior, boundary arithmetic, permissions, unknown tools, and failures.</p>
              </div>
              <button className="btn btn-primary" onClick={handleTriggerEval} disabled={loading}>
                <Play size={16} /> Run Evaluation Suite
              </button>
            </div>

            <div className="card">
              <div className="card-title">Evaluation Runs History</div>
              <table>
                <thead>
                  <tr>
                    <th>Run Label</th>
                    <th>Agent Version</th>
                    <th>Pass Rate</th>
                    <th>Passed / Total</th>
                    <th>Duration</th>
                    <th>Executed At</th>
                  </tr>
                </thead>
                <tbody>
                  {evalRuns.map((e) => (
                    <tr key={e.id}>
                      <td style={{ fontWeight: 600 }}>{e.run_label || 'Evaluation Run'}</td>
                      <td><span className="badge badge-purple">v{e.agent_version}</span></td>
                      <td>
                        <span className={`badge ${e.pass_rate >= 90 ? 'badge-success' : 'badge-danger'}`}>
                          {e.pass_rate}%
                        </span>
                      </td>
                      <td>{e.passed_cases} / {e.total_cases}</td>
                      <td>{Math.round(e.duration_ms)} ms</td>
                      <td>{new Date(e.started_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Most Recent Per-Case Breakdown */}
            {evalRuns.length > 0 && evalRuns[0].results_detail && (
              <div className="card">
                <div className="card-title">Latest Suite Breakdown: {evalRuns[0].run_label}</div>
                <table>
                  <thead>
                    <tr>
                      <th>Case ID</th>
                      <th>Category</th>
                      <th>Description</th>
                      <th>Expected vs Actual Status</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evalRuns[0].results_detail.map((c) => (
                      <tr key={c.case_id}>
                        <td><code>{c.case_id}</code></td>
                        <td><span className="badge badge-info">{c.category}</span></td>
                        <td>{c.description}</td>
                        <td><span className="badge badge-secondary">{c.actual_status}</span></td>
                        <td>
                          {c.passed ? (
                            <span className="badge badge-success">PASSED</span>
                          ) : (
                            <span className="badge badge-danger">FAILED: {c.diagnosis}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab D: Tools & Policies */}
        {activeTab === 'tools' && (
          <div>
            <div className="page-header">
              <div>
                <h1 className="page-title">Registered Tools & Policies</h1>
                <p className="page-desc">Explicit allowlist of registered tools, schemas, permission tiers, and approval requirements.</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '20px' }}>
              {tools.map((t) => (
                <div key={t.name} className="card">
                  <div className="card-title">
                    <span>{t.name}</span>
                    <span className={`badge ${t.requires_approval ? 'badge-warning' : 'badge-success'}`}>
                      {t.requires_approval ? 'Approval Required' : 'Autonomous'}
                    </span>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '14px' }}>
                    {t.description}
                  </p>
                  <div style={{ fontSize: '0.8rem', marginBottom: '8px' }}>
                    <strong>Permission Level:</strong> <span className="badge badge-purple">{t.permission_level}</span>
                  </div>
                  <div style={{ marginTop: '12px' }}>
                    <strong style={{ fontSize: '0.8rem' }}>Schema:</strong>
                    <div className="trace-body" style={{ maxHeight: '180px' }}>
                      {JSON.stringify(t.input_schema, null, 2)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab E: Approvals & Governance */}
        {activeTab === 'approvals' && (
          <div>
            <div className="page-header">
              <div>
                <h1 className="page-title">Human-in-the-Loop Governance</h1>
                <p className="page-desc">Enforce human oversight for protected actions (e.g. incident creation, production changes).</p>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Approval Requests ({approvals.length})</div>
              {approvals.length === 0 ? (
                <p style={{ color: 'var(--text-muted)' }}>No approval requests in the pipeline.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Tool</th>
                      <th>Requested By</th>
                      <th>Parameters (Tamper-Resistant Fingerprint)</th>
                      <th>Reviewer / Reason</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvals.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <span className={`badge ${
                            a.status === 'pending' ? 'badge-warning' :
                            a.status === 'approved' ? 'badge-success' : 'badge-danger'
                          }`}>
                            {a.status}
                          </span>
                        </td>
                        <td style={{ fontWeight: 600 }}>{a.tool_name}</td>
                        <td>{a.requested_by}</td>
                        <td>
                          <div style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                            {JSON.stringify(a.action_parameters)}
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                              SHA: {a.action_fingerprint.slice(0, 16)}...
                            </div>
                          </div>
                        </td>
                        <td>
                          {a.reviewed_by ? `${a.reviewed_by} (${a.decision_reason || 'N/A'})` : 'Awaiting Review'}
                        </td>
                        <td>
                          {a.status === 'pending' ? (
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button 
                                className="btn btn-success" 
                                style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                                onClick={() => handleApprovalDecision(a.id, 'approved')}
                              >
                                Approve
                              </button>
                              <button 
                                className="btn btn-danger" 
                                style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                                onClick={() => handleApprovalDecision(a.id, 'rejected')}
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Decided</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* Tab F: Settings & Docs */}
        {activeTab === 'settings' && (
          <div>
            <div className="page-header">
              <div>
                <h1 className="page-title">Platform Configuration & Documentation</h1>
                <p className="page-desc">System configuration, security architecture, and threat mitigation.</p>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Environment & Mode Configuration</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.9rem' }}>
                <div><strong>Product Branding:</strong> Virar AI</div>
                <div><strong>Backend Framework:</strong> FastAPI + SQLAlchemy 2.x</div>
                <div><strong>Execution Engine:</strong> Deterministic Offline Mode (Active)</div>
                <div><strong>LLM Provider:</strong> Configurable (No paid keys required)</div>
                <div><strong>Database:</strong> SQLite aiosqlite (Local) / PostgreSQL Ready</div>
                <div><strong>Secret Redaction:</strong> Active regex scanner on all traces & logs</div>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Security & Threat Model Summary</div>
              <ul style={{ paddingLeft: '20px', lineHeight: '1.8', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                <li><strong>No Arbitrary Code Execution:</strong> Tools are strictly allowlisted; arbitrary shell or eval calls are rejected before execution.</li>
                <li><strong>Self-Approval Prevention:</strong> Requesting agents and actors cannot approve their own protected actions.</li>
                <li><strong>Parameter Integrity Fingerprinting:</strong> Parameters are cryptographically hashed using SHA-256 to guarantee that arguments cannot be tampered with between request and execution.</li>
                <li><strong>Credential Redaction:</strong> Automated redaction masks tokens, API keys, and sensitive headers before persistence in traces or databases.</li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
