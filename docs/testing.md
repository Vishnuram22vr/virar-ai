# Testing & Quality Assurance — Virar AI

## 1. Test Strategy
Virar AI employs a multi-layered testing strategy combining unit tests, integration tests, security assertion tests, and deterministic evaluation benchmark suites.

## 2. Test Execution Commands

### Backend Pytest Suite
```bash
cd backend
python -m pytest tests/test_platform.py -v -c pytest.ini
```

**Verified Test Cases:**
- `test_health_and_readiness`: Tests `/health` and `/ready` DB connectivity endpoints.
- `test_tool_registry_and_calculator`: Validates calculator arithmetic and division-by-zero boundary handling.
- `test_agent_run_execution_and_traces`: Verifies run lifecycle, step duration, token counting, and chronological trace emission.
- `test_approval_governance_lifecycle`: Validates human-in-the-loop approvals, self-approval prevention (403 Forbidden), and approved execution.
- `test_sensitive_data_redaction`: Verifies redaction of API keys, bearer tokens, and secrets from traces and payloads.
- `test_parameter_tamper_detection`: Verifies cryptographic SHA-256 parameter hashing against tampering.
- `test_evaluation_suite_run`: Executes the 20-case deterministic benchmark suite and ensures pass rate > 90%.

### Frontend Build & Typecheck
```bash
cd frontend
npm run build
```
Validates TypeScript compilation and Vite production bundle generation.
