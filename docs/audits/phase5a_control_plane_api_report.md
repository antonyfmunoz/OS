# Phase 5A: Control Plane Interface (HTTP API) — Audit Report

**Date:** 2026-04-26
**Status:** COMPLETE

## Files Changed

| File | Action |
|------|--------|
| `umh/control/__init__.py` | NEW — package marker |
| `umh/control/__main__.py` | NEW — module entry point |
| `umh/control/api.py` | NEW — FastAPI control plane API |
| `tests/unit/test_phase5a.py` | NEW — 31 tests |
| `requirements.txt` | Added `fastapi>=0.115,<1.0` |

## Architecture

```
External Actors                    Control Plane                Internal Systems
─────────────────    ───────────────────────────────    ──────────────────────
                     ┌──────────────────────────────┐
  CLI / curl    ──→  │  FastAPI (localhost:8000)     │
  Future UI     ──→  │  X-API-Key auth middleware    │
  Agents        ──→  │                              │
  Automation    ──→  │  POST /execute          ────→│──→ engine.execute()
                     │  GET  /approvals        ────→│──→ ApprovalStore
                     │  GET  /approvals/{id}   ────→│──→ ApprovalStore
                     │  POST /approvals/{id}/approve│──→ ApprovalStore
                     │  POST /approvals/{id}/deny  │──→ ApprovalStore
                     │  GET  /metrics          ────→│──→ metrics.get_metrics()
                     │  GET  /health (public)       │
                     └──────────────────────────────┘
```

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/execute` | Yes | Execute operation through engine |
| GET | `/approvals` | Yes | List all approvals (?status=pending) |
| GET | `/approvals/{id}` | Yes | Get specific approval |
| POST | `/approvals/{id}/approve` | Yes | Approve pending approval |
| POST | `/approvals/{id}/deny` | Yes | Deny pending approval |
| GET | `/metrics` | Yes | Full execution metrics |

## Execute Request/Response

Request:
```json
{
  "operation": "computer_click",
  "inputs": {"x": 100, "y": 200},
  "execution_class": "side_effect",
  "timeout_s": 30,
  "sandbox": false
}
```

Response: full `ExecutionResult.to_dict()` — same schema as internal.

## Authentication

- Header: `X-API-Key`
- Env var: `UMH_API_KEY`
- `/health` is exempt (load balancer probes)
- Missing key → 401
- Wrong key → 401
- `UMH_API_KEY` not set → 503

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 401 | Invalid or missing API key |
| 404 | Approval not found |
| 409 | Conflict (expired, already approved, consumed) |
| 422 | Invalid request body |
| 503 | API key not configured |

## Safety Constraints

1. No execution logic duplicated — all routes delegate to existing modules
2. No direct access to internal modules from API handlers
3. API key required for all mutating and reading endpoints
4. No schema changes to ExecutionRequest/ExecutionResult
5. No guard architecture modifications
6. No async agent orchestration
7. No database changes
8. No shell allowlist broadening

## Running the API

```bash
UMH_API_KEY=your-secret python3 -m umh.control.api
# or
UMH_API_KEY=your-secret uvicorn umh.control.api:app --host 127.0.0.1 --port 8000
```

## Test Results

```
Phase 5A: 31 passed in 1.38s
Phases 4D+4E+4F+5A+capabilities: 163 passed in 34.39s
```

Test coverage:
- A. Health endpoint — public, no auth (2 tests)
- B. Auth enforcement — 401/503 for all protected endpoints (6 tests)
- C. Execute endpoint — shell, screenshot, mutation, approval flow (7 tests)
- D. Approvals API lifecycle — list, get, approve, deny, errors (11 tests)
- E. Metrics endpoint — structure validation (4 tests)
- F. Full lifecycle — execute→reject→approve→execute→succeed→consumed→replay blocked (1 test)

## Validation

```bash
python3 -c "import umh; print('OK')"          # OK
python3 -m umh.execution.approvals list        # No approvals found.
python3 -m umh.execution.metrics               # Shows counters
```

## What This Enables

- Single authenticated entry point for all external interaction
- CLI can be rewritten to call API instead of direct module imports
- Future UI/dashboard connects to same API
- Agent-to-agent communication via HTTP
- Standardized error codes and response formats
