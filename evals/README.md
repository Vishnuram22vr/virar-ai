# Evaluation Suites — Virar AI

## Core Suite (`core_suite_v1.json`)
The core evaluation suite contains 20 deterministic benchmark cases designed to test reliability, boundary handling, and security policies without requiring third-party model access.

### Benchmark Distribution
1. **Normal Arithmetic Operations (5 cases):** Addition, subtraction, multiplication, division, and exponents.
2. **Boundary & Error Handling (2 cases):** Division by zero and exponent overflow (>100).
3. **Infrastructure Health Lookups (4 cases):** Healthy auth service, degraded payment gateway, primary database, and AI inference cluster.
4. **Service Outages (1 case):** Simulated service downtime generating structured outage errors.
5. **Security & Injection Resistance (3 cases):** Rejection of arbitrary tools (`bash_terminal`, `python_eval`) and prompt injection bypass attempts.
6. **Governance & Approvals (2 cases):** Verification that protected actions pause execution and transition to `waiting_approval`.
7. **Fallback & Precision (3 cases):** Non-tool conversational prompts, floating-point precision, and negative number arithmetic.
