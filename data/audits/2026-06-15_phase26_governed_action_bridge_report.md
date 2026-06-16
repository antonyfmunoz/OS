# Phase 26 — Governed Action Bridge

**Date:** 2026-06-15
**Status:** COMPLETE
**Tests:** 48/48 passing
**Lines:** ~1,960 new across 7 files, ~30 modified in 2 files

---

## What It Does

Phase 26 bridges workspace observation (Phase 25) to governed action. The operator can now express intent ("restart the webhook container") and UMH routes it through a governed chain:

```
Intent → ActionCatalog → Preconditions → Governance → ExecutionCoordinator → WorkstationExecutor → Proof → Review
```

**This is pure composition.** No new execution authority was created. Every action flows through existing Phase 13-15 infrastructure.

---

## Architecture

### Data-Driven Actions

Actions are data, not code. Each action is an `ActionDefinition` with a command template, risk level, preconditions, and parameter schema. Adding a new action means registering a definition — no Python required.

### Composition Pattern

ActionBridge composes 4 existing subsystems:
- **ActionCatalog** — keyword-based action resolution (no LLM)
- **WorkspaceObservationEngine** (Phase 25) — precondition checks against live workspace state
- **ExecutionCoordinator** (Phase 13) — plan lifecycle + governance gates
- **WorkstationExecutor** (Phase 15A) — actual execution via cpu_gate

### Safety Guarantees

| Guarantee | Mechanism |
|---|---|
| No shell injection | `_SHELL_UNSAFE` regex rejects `[;&\|$(){}!<>\\]` in all parameters |
| Medium+ risk never auto-approves | `_RISK_REQUIRES_APPROVAL["medium"] = True` at execution_coordinator.py:568 |
| No raw subprocess | All commands through `gated_subprocess_run()` (cpu_gate) |
| No LLM calls | Deterministic keyword matching in catalog.resolve() |
| Full audit trail | Every action produces ExecutionProof via EventSpine |

---

## Seed Actions (7)

| action_id | Risk | Category | Command Template |
|---|---|---|---|
| `list_containers` | safe | observation | `docker ps -a --format '{{.Names}}\t{{.Status}}'` |
| `container_logs` | safe | observation | `docker logs --tail {lines} {container_name}` |
| `service_health` | safe | observation | `docker inspect --format='{{.State.Health.Status}}' {container_name}` |
| `run_tests` | low | test | `python3 -m pytest {test_path} -x` |
| `run_lint` | safe | test | `ruff check {target_path}` |
| `git_status` | safe | observation | `git -C {repo_path} status` |
| `restart_container` | **medium** | container | `docker restart {container_name}` |

**Deferred:** `create_worktree`, `stop_container`, `start_container` — after bridge proves stable.

---

## Files

### New (7)
| File | Layer | Lines |
|---|---|---|
| `substrate/organism/action_catalog.py` | substrate | 308 |
| `substrate/organism/action_bridge.py` | substrate | 416 |
| `substrate/organism/action_voice_contract.py` | substrate | 80 |
| `transports/api/cockpit_action_bridge_routes.py` | transport | 113 |
| `cockpit/src/renderer/stores/actionsStore.ts` | cockpit | 123 |
| `cockpit/src/renderer/panels/ActionsPanel.tsx` | cockpit | 186 |
| `tests/test_phase26_action_bridge.py` | tests | 704 |

### Modified (2)
| File | Change |
|---|---|
| `transports/api/cockpit.py` | +16 lines — mount action bridge router |
| `substrate/canonical_types.py` | +14 lines — 9 type registrations + 3 legacy allowlist |

---

## API Routes (6)

| Route | Method | Purpose |
|---|---|---|
| `/actions/catalog` | GET | List all actions with precondition state |
| `/actions/catalog/{action_id}` | GET | Single action with precondition state |
| `/actions/execute` | POST | Execute an action (body: action_id, parameters) |
| `/actions/{plan_id}/approve` | POST | Approve pending action |
| `/actions/status/{request_id}` | GET | Check action status |
| `/actions/history` | GET | Recent action results |

---

## Test Coverage (48 tests)

| Class | Tests |
|---|---|
| TestActionTypes | 5 — enum values, string conversion, completeness |
| TestActionDefinition | 6 — construction, serialization, parameter validation |
| TestActionCatalog | 9 — seed defaults, resolve by ID/text, category filtering |
| TestActionBridge | 13 — full lifecycle, approval flow, shell injection, preconditions |
| TestIntentContract | 4 — translate with/without action_id, parameter preservation |
| TestCockpitRoutes | 3 — import, configure, router routes |
| TestTypeRegistration | 3 — canonical types, import verification |
| TestIntegration | 5 — end-to-end lifecycle, approval, precondition blocking |

---

## Gate Results

| Gate | Status |
|---|---|
| Instance leak | CLEAN |
| Projection leak | CLEAN (pre-existing violations only) |
| Dependency direction | CLEAN (pre-existing violations only) |
| Type divergence | CLEAN (3 legacy files allowlisted) |
| CPU gate | No raw subprocess |

---

## What This Phase Does NOT Do

- No new executor types — uses existing WorkstationExecutor
- No voice recognition — just the data contract (IntentActionRequest)
- No LLM calls — deterministic keyword matching
- No autonomous execution — governance gates on every action
- No deployment authority — deploy actions excluded from seed catalog
- No remote desktop or keyboard/mouse automation
