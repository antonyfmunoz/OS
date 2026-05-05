# Worker Node Organism Doctrine v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Doctrine

Worker nodes operate like organism execution cells. Each worker follows
a biological lifecycle: perceive → plan → execute → observe → report →
emit feedback. This is not a metaphor — it is the actual state machine.

## Worker Lifecycle States

```
BOOTING → IDLE → CLAIMING_WORK → VALIDATING_WORK → PLANNING →
EXECUTING → OBSERVING → REPORTING → FEEDBACK_SYNC → COMPLETE
```

At any point, a worker may transition to:
- `WAITING_FOR_ADVISOR_APPROVAL` — governance gate requires human input
- `BLOCKED` — denied, invalid, or paused by founder
- `FAILED` — error or stop command received

Terminal states: `FAILED`, `COMPLETE`. No transitions out.

## Worker Modes

| Mode | Behavior |
|------|----------|
| `AUTO` | Default. Proceeds through loop, pauses only at governance gates. |
| `MANUAL_FALLBACK` | Waits for human instruction at every step. |
| `PAUSED` | Frozen. Cannot claim work. |
| `DISABLED` | Off. Cannot claim work. |

## Worker Roles

- `GUI_COMPUTER_USE` — can operate a screen via computer use
- `BROWSER_AUTOMATION` — can run headless browser tasks
- `API_WORKER` — can call external APIs
- `FILE_WORKER` — can read/write local files
- `LLM_WORKER` — can perform inference
- `MANUAL_OPERATOR` — requires human hands

## Key Types

- `WorkerProfile` — static identity: ID, node, roles, capabilities, mode
- `WorkerRuntimeState` — live state: current state, active work order,
  pending approvals, action counts, error detail
- `WorkerAction` — one discrete action in an execution plan
- `WorkerFeedbackEvent` — post-execution feedback for organism learning

## State Transition Enforcement

`WorkerRuntimeState.transition()` enforces allowed transitions via the
`WORKER_STATE_TRANSITIONS` dict. Invalid transitions raise `ValueError`.
This prevents state corruption at the contract level.

## Files

- `eos_ai/substrate/worker_node_contracts.py` — types and state machine
- `eos_ai/substrate/worker_node_runtime.py` — pure runtime functions
