# Threat Model & Security Posture — Virar AI

## 1. Scope and Security Objectives
Virar AI is engineered to observe and govern AI agents. AI agents inherently interact with external tools and make semi-autonomous decisions based on unstructured user prompts. Our threat model addresses prompt injection, unauthorized actions, data leakage, and argument tampering.

## 2. Threat Analysis & Mitigations

| Threat Vector | Potential Impact | Virar AI Defense / Mitigation |
| :--- | :--- | :--- |
| **Prompt Injection** | Attacker instructs agent to ignore rules or call dangerous external tools. | **Strict Tool Registry Allowlist:** Unregistered tools (such as `bash`, `exec`, `eval`) are rejected prior to execution. Prompt instructions cannot bypass the Python backend allowlist. |
| **Unauthorized Tool Calls** | Agent attempts to invoke privileged actions without authorization. | **Permission Tiers & Server Enforcement:** Tool definitions specify `read`, `write`, or `admin`. High-impact tools require explicit human approval. |
| **Self-Approval Bypass** | Agent or rogue actor attempts to approve its own protected execution. | **Server-side Governance Rule:** Backend checks `requester != reviewer`. If identical, an HTTP 403 Forbidden is returned. |
| **Action Parameter Tampering** | Attacker alters arguments after human reviewer approved them (TOCTOU). | **Cryptographic SHA-256 Fingerprint:** Parameter hashes are validated at both approval request and execution time. Any alteration invalidates the approval. |
| **Secret / Data Leakage** | API keys, Bearer tokens, or passwords leaked in trace logs or dashboard. | **Automated Redaction Engine:** Recursive regex scanner inspects all inputs, arguments, results, and trace metadata, replacing secrets with `[REDACTED]`. |
| **Denial of Service / Infinite Loop** | Agent gets stuck in recursion or executes oversized computations. | **Execution Step Bounds:** Maximum steps per run (15 default), timeouts (60s default), and mathematical bounds (e.g. exponent limit of 100). |

## 3. Production Hardening Recommendations
- Switch `DEV_AUTH_MODE=false` in production.
- Configure enterprise SSO or OAuth2 with JWT validation for the reviewer portal.
- Deploy database over SSL on PostgreSQL.
- Enable rate limiting on public run dispatch endpoints.
