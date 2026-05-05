# Phase 7B: Tool Integration Layer (External Capability System) — Completion Report

**Date:** 2026-04-27
**Status:** Complete

---

## Agents Used

| Agent | Task | Output |
|-------|------|--------|
| 1 — Tool Adapter | ToolsAdapter (ExternalCapabilityAdapter), HTTP client via urllib | umh/adapters/tools_adapter.py, umh/tools/registry.py, 25 tests |
| 2 — Guard Integration | Security guard tool operation checks, domain allowlist | umh/security/execution_guard.py updates, 28 tests |
| 3 — API + CLI | Tool endpoints, CLI commands, frontend tool display | umh/control/api.py updates, umh/control/cli.py updates, frontend/ updates, 24 tests |
| 4 — Templates + Boundary | Planner templates (fetch_data, send_webhook), boundary audit tests | umh/planning/templates.py updates, umh/planning/validator.py updates, 37 tests |
| Main — Integrator | Compile, format, regression fix, validation, report | This report |

---

## Architecture: Additive + Minimal Modification

Phase 7B adds a tool integration layer that routes all external HTTP actions through the existing execution spine: planning → validation → task → execution engine → guard → adapter.

```
┌──────────────────────────────────────────────────────────┐
│                    UMH SYSTEM                            │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  Execution   │   │ Orchestrator │   │   Approval   │  │
│  │   Engine     │   │  + Worker    │   │    Store     │  │
│  └─────────────┘   └──────────────┘   └──────────────┘  │
│         ▲                                                │
│         │                                                │
│  ┌──────┴─────────────────────────────────────────────┐  │
│  │            SpineExecutionBackend                    │  │
│  │  _execute_external() → adapter registry            │  │
│  │  + "tool_action" → ToolsAdapter                    │  │
│  └────────────────────────────────────────────────────┘  │
│         ▲                                                │
│  ┌──────┴─────────────────────────────────────────────┐  │
│  │              Security Guard                         │  │
│  │  + check_tool_operation()                           │  │
│  │  + domain allowlist validation                      │  │
│  │  + mutating tools → REQUIRES_APPROVAL               │  │
│  └────────────────────────────────────────────────────┘  │
│         ▲                                                │
│  ┌──────┴─────────────────────────────────────────────┐  │
│  │            Planning Layer                           │  │
│  │  + fetch_data template (http_get)                   │  │
│  │  + send_webhook template (http_post/webhook)        │  │
│  │  + http_request in _KNOWN_OPERATIONS                │  │
│  └────────────────────────────────────────────────────┘  │
│         ▲                                                │
│  ┌──────┴─────────────────────────────────────────────┐  │
│  │         Tool Registry + Definitions                 │  │
│  │  http_get (non-mutating)                            │  │
│  │  http_post (mutating → approval)                    │  │
│  │  webhook (mutating → approval)                      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/tools/registry.py` | ~115 | Tool definitions, domain allowlists, validation |
| `umh/adapters/tools_adapter.py` | ~115 | HTTP client via urllib.request, ExternalCapabilityAdapter impl |
| `tests/unit/test_phase7b_tool_adapter.py` | ~300 | Adapter + registry tests (25) |
| `tests/unit/test_phase7b_guard_integration.py` | ~350 | Guard tool operation tests (28) |
| `tests/unit/test_phase7b_api_cli.py` | ~340 | API endpoint + CLI command tests (24) |
| `tests/unit/test_phase7b_templates.py` | ~300 | Template + planner tests (26) |
| `tests/unit/test_phase7b_boundary_audit.py` | ~150 | Boundary invariant tests (11) |

## Files Modified

| File | Change | Impact |
|------|--------|--------|
| `umh/security/execution_guard.py` | +check_tool_operation(), +routing in check_execution() | Guards tool operations, domain allowlist |
| `umh/adapters/umh_execution.py` | +ToolsAdapter registration, +tool_action classification | Routes http_request/tool_* to ToolsAdapter |
| `umh/planning/templates.py` | +fetch_data, +send_webhook templates | Deterministic plans for HTTP tools |
| `umh/planning/validator.py` | +http_request to _KNOWN_OPERATIONS | Validates tool execution plans |
| `umh/control/api.py` | +3 tool endpoints (GET /tools, GET /tools/{name}, POST /tools/{name}/execute) | Additive only |
| `umh/control/cli.py` | +2 tool commands (tools, tool-run) | Routes through planning layer, not execution engine directly |
| `frontend/index.html` | +Tools metric card in dashboard grid | Additive only |
| `frontend/app.js` | +tool info in task detail steps, +tools count in metrics | Additive only |

---

## Tool Registry

### ToolDefinition

```python
@dataclass(frozen=True)
class ToolDefinition:
    name: str              # "http_get", "http_post", "webhook"
    operation: str         # "http_request"
    description: str
    required_inputs: list[str]
    optional_inputs: list[str]
    mutating: bool         # True → REQUIRES_APPROVAL
    allowed_domains: frozenset[str]
    timeout_s: int
    execution_class: str   # "side_effect"
```

### Built-in Tools

| Name | Mutating | Required | Description |
|------|----------|----------|-------------|
| `http_get` | No | url | HTTP GET request |
| `http_post` | Yes | url | HTTP POST request |
| `webhook` | Yes | url | Send webhook notification |

### Domain Allowlist

```python
DEFAULT_ALLOWED_DOMAINS = {
    "api.github.com",
    "hooks.slack.com",
    "api.linear.app",
    "httpbin.org",
    "jsonplaceholder.typicode.com",
}
```

---

## Tools Adapter

`ToolsAdapter` extends `ExternalCapabilityAdapter`:
- `adapter_name = "tools_adapter"`
- `capability_type = "tool_action"`
- Uses `urllib.request` (stdlib only — no `requests` dependency)
- 1MB response body limit
- User-Agent: `UMH-ToolsAdapter/1.0`
- SSL error handling
- Configurable timeout per tool definition

---

## Security Guard Integration

### check_tool_operation()

1. Validates tool exists in registry
2. Validates required inputs present
3. Validates URL domain against allowlist
4. Mutating tool → `REQUIRES_APPROVAL`
5. Non-mutating + valid domain → `ALLOW`
6. Unknown domain → `DENY`

### Routing in check_execution()

| Operation | Handler |
|-----------|---------|
| `http_request` | `check_tool_operation()` |
| `tool_*` prefix | `check_tool_operation()` |
| `shell_command` | `check_shell_command()` |
| `file_*` | `check_file_operation()` |
| `computer_*` | `check_computer_operation()` |

---

## Planning Templates

| Template | Triggers On | Operation | Tool |
|----------|-------------|-----------|------|
| `fetch_data` | "fetch", "get data", "http get" | http_request | http_get |
| `send_webhook` | "webhook", "notify", "send notification" | http_request | webhook |

Both produce `ExecutionPlan` with `execution_class="side_effect"` and `source=PlanSource.TEMPLATE`.

---

## API Endpoints

| Endpoint | Method | Scope | Description |
|----------|--------|-------|-------------|
| `/tools` | GET | tools:read | List all registered tools |
| `/tools/{name}` | GET | tools:read | Get tool definition |
| `/tools/{name}/execute` | POST | tools:write | Execute tool through engine |

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `tools [--json]` | List registered tools |
| `tool-run <name> --url URL [--method M] [--body B] [--json]` | Execute tool through planning layer |

### CLI Bypass Fix

The initial implementation of `cmd_tool_run` directly imported `from umh.execution.engine import execute`, violating the bypass invariant enforced by Phase 6C and 6F tests. This was refactored to route through `create_plan()` → `execute_plan()`, matching the pattern used by `cmd_run`. The CLI never touches the execution engine directly.

---

## Boundary Verification

### Non-Invasion Proof

| Check | Result |
|-------|--------|
| No HTTP imports in planning module | PASS |
| No HTTP imports in orchestrator module | PASS |
| No HTTP imports in memory module | PASS |
| ToolsAdapter uses only urllib (stdlib) | PASS |
| Tool registry has no execution engine imports | PASS |
| CLI has no direct execution engine imports | PASS |
| Guard routes mutating tools to REQUIRES_APPROVAL | PASS |
| Templates produce valid ExecutionPlan objects | PASS |
| Template steps use execution_class="side_effect" | PASS |
| No HTTP request execution in planning module | PASS |

### Import Graph (tool module)

```
umh/tools/registry.py           → (stdlib only: logging, dataclasses, urllib.parse)
umh/adapters/tools_adapter.py   → umh.adapters.base (ExternalCapabilityAdapter)
                                → umh.tools.registry
                                → umh.execution.contract (ExecutionRequest, ExecutionResult)
umh/security/execution_guard.py → umh.tools.registry (for tool validation)
umh/planning/templates.py       → umh.planning.models (ExecutionPlan, etc.)
```

No reverse dependencies: nothing in execution core, orchestrator, or memory imports from umh.tools.

---

## Tests

### Phase 7B Tests

| Suite | Tests | Status |
|-------|-------|--------|
| test_phase7b_tool_adapter.py | 25 | Pass |
| test_phase7b_guard_integration.py | 28 | Pass |
| test_phase7b_api_cli.py | 24 | Pass |
| test_phase7b_templates.py | 26 | Pass |
| test_phase7b_boundary_audit.py | 11 | Pass |
| **Total Phase 7B** | **114** | **All pass** |

### Regression

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 7A (memory) | 91 | Pass |
| Phase 6H (config, API hardening) | 30 | Pass (isolated) |
| Phase 6G (API contract) | 14 | Pass |
| Phase 6F (CLI operator) | 29 | Pass |
| Phase 6E (retry, task control, timeline, worker) | 92 | Pass |
| Phase 6D (execution fabric) | 50 | Pass |
| Phase 6C (CLI) | 11 | Pass |
| Phase 6A+6B (spine, meta harness) | 122 | Pass |
| Phase 5A (control plane) | 31 | Pass |
| **Total verified** | **584+** | **All pass** |

### Validation

| Check | Result |
|-------|--------|
| `python3 -c "import umh"` | OK |
| `python3 -m py_compile` all Phase 7B files | All OK |
| `ruff format` all Phase 7B files | All unchanged |
| `python3 -m umh.execution.metrics` | OK |
| No HTTP imports in planning/orchestrator/memory | PASS |
| No execution engine imports in CLI | PASS |
| Tool registry import | 3 tools registered |
| Guard import | OK |
| Adapter import | tools_adapter, tool_action |
| Frontend boundary check | PASS |

---

## Hard Invariant Verification

| # | Invariant | Status |
|---|-----------|--------|
| 1 | All external actions through execution engine → guard → adapter | PASS |
| 2 | No direct API calls from planner/orchestrator/memory | PASS |
| 3 | Mutating tools require approval | PASS |
| 4 | Domain allowlist enforced | PASS |
| 5 | CLI routes through planning layer (no bypass) | PASS |
| 6 | No execution engine modification (core logic) | PASS |
| 7 | No orchestrator logic modification | PASS |
| 8 | No approval system modification | PASS |
| 9 | No schema changes to existing tables | PASS |
| 10 | No implicit state mutations | PASS |

---

## Known Limitations

1. **Domain allowlist is static** — adding new domains requires code change (no runtime API)
2. **HTTP only** — no gRPC, WebSocket, or other transport protocols
3. **No response caching** — each request hits the network
4. **No retry logic** — failed requests are not retried (operator can re-run)
5. **1MB response limit** — large responses are truncated
6. **Pre-existing test isolation** — test_phase6h_config_logging fails when run after test_phase6h_api_hardening (UMH_WORKER_AUTO_START env var collision, not Phase 7B)

---

## MVP Readiness

**~99%** (unchanged from Phase 7A)

| Area | Score | Change |
|------|-------|--------|
| Core loop | 100% | — |
| API surface | 100% | — |
| CLI surface | 100% | — |
| Web UI | 98% | — |
| Task persistence | 95% | — |
| Worker execution | 98% | — |
| Operator controls | 100% | — |
| Intelligence bridge | 95% | — |
| Observability | 100% | — |
| Documentation | 98% | — |
| Reliability | 95% | — |
| Memory & Context | 90% | — |
| **Tool Integration** | **90%** | **NEW** |

---

## Success Condition Verification

> "All external actions through execution engine → guard → adapter"

**VERIFIED.** Tools are defined in the registry, validated by the guard (domain check, input validation, mutation flag), executed by ToolsAdapter through the SpineExecutionBackend's external adapter routing.

> "No direct API calls from planner/orchestrator/memory"

**VERIFIED.** Boundary audit tests confirm zero HTTP library imports in planning, orchestrator, and memory modules. The tools_adapter.py uses urllib (stdlib) and is only invoked through the execution engine.

> "CLI routes through planning layer"

**VERIFIED.** `cmd_tool_run` builds a PlanObjective, routes through `create_plan()` → `execute_plan()`. Zero direct imports from `umh.execution.engine` in CLI. Phase 6C and 6F bypass invariant tests pass.

> "Mutating tools require approval"

**VERIFIED.** Guard's `check_tool_operation()` returns `REQUIRES_APPROVAL` for tools with `mutating=True` (http_post, webhook). Non-mutating tools (http_get) with allowed domains get `ALLOW`.
