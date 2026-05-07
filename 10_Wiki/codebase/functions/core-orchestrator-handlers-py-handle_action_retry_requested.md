---
type: codebase-function
file: core/orchestrator/handlers.py
line: 218
generated: 2026-05-07
---

# handle_action_retry_requested

**File:** [[core-orchestrator-handlers-py]] | **Line:** 218
**Signature:** `handle_action_retry_requested(context) → dict[str, Any]`

Retry a previously-failed action via the Control Plane.

The loop emits `action_retry_requested` only when the original
action was retry-eligible, but the handler re-checks with
`should_retry()` so that:
...

## Calls

- [[core-action_system-control_plane-py-run_action]]
- [[core-orchestrator-handlers-py-_action_from_context]]
- [[core-orchestrator-handlers-py-_append_operator_notice]]
