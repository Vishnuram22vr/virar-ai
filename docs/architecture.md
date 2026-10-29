# Architecture & System Design — Virar AI

## 1. Overview
**Virar AI** is a modular platform for observing, evaluating, debugging, and governing AI agents. It captures real agent interactions, persists granular chronological execution traces, enforces human-in-the-loop approvals for consequential actions, and runs deterministic benchmark evaluation suites.

## 2. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Frontend["React 19 + TypeScript + Vite Dashboard"]
        UI_Overview["Overview & Real-time Metrics"]
        UI_Runs["Agent Runs & Chronological Traces"]
        UI_Evals["Deterministic Evals & Regressions"]
        UI_Tools["Registered Tool Schemas & Policies"]
        UI_Approvals["Human Governance & Approval Portal"]
    end

    subgraph API["FastAPI Modular Backend (Python 3.11+)"]
        AuthMiddleware["Dev / Production Auth & RBAC"]
        APIRoutes["REST API Endpoints (/api/v1)"]
        ExecutionEngine["Agent Execution Engine & Planner"]
        EvalRunner["Evaluation Benchmark Runner"]
        GovernanceEngine["Approval & Tamper-Detection Engine"]
        Redactor["Sensitive Data & Secret Redactor"]
    end

    subgraph ToolCatalog["Explicit Tool Registry (Allowlist)"]
        T1["calculator (read)"]
        T2["service_health_lookup (read)"]
        T3["create_incident_ticket (admin, requires approval)"]
    end

    subgraph Storage["Storage Layer"]
        DB[(SQLite / PostgreSQL via SQLAlchemy 2.x)]
        EvalsDir["Versioned Evaluation Datasets (JSON)"]
    end

    UI_Overview --> APIRoutes
    UI_Runs --> APIRoutes
    UI_Evals --> APIRoutes
    UI_Tools --> APIRoutes
    UI_Approvals --> APIRoutes

    APIRoutes --> AuthMiddleware
    AuthMiddleware --> ExecutionEngine
    AuthMiddleware --> EvalRunner
    AuthMiddleware --> GovernanceEngine

    ExecutionEngine --> Redactor
    ExecutionEngine --> ToolCatalog
    GovernanceEngine --> ToolCatalog
    EvalRunner --> ExecutionEngine

    Redactor --> DB
    ExecutionEngine --> DB
    GovernanceEngine --> DB
    EvalRunner --> EvalsDir
```

## 3. Core Modules
- **Agent Execution Engine (`app/agent/runner.py`)**: Executes tasks, handles step limits and timeouts, formats trace spans, and records real token usage and cost metrics.
- **Trace & Observability (`app/models/entities.py`)**: Stores chronological spans (`run_created`, `planning`, `tool_call`, `tool_result`, `approval_requested`, `approval_decided`, `completion`, `failure`).
- **Tool Allowlist & Registry (`app/tools/base.py`, `app/tools/implementations.py`)**: Explicit allowlist preventing arbitrary code or unregistered shell invocation.
- **Governance & Approval System (`app/security/governance.py`)**: Cryptographic SHA-256 parameter hashing prevents argument tampering. Self-approval is strictly forbidden.
- **Deterministic Evaluation Suite (`app/evaluations/runner.py`)**: Runs 20 unit benchmarks testing arithmetic limits, zero-division, service outages, injection resistance, and unknown tools.
