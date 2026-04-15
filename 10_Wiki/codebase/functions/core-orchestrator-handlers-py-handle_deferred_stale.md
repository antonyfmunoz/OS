---
type: codebase-function
file: core/orchestrator/handlers.py
line: 94
generated: 2026-04-12
---

# handle_deferred_stale

**File:** [[core-orchestrator-handlers-py]] | **Line:** 94
**Signature:** `handle_deferred_stale(context) → dict[str, Any]`

React to a stale deferred action.

The loop emits this when a deferred action has been waiting longer
than `LoopConfig.stale_deferred_seconds`. The handler does three
things:
...

## Calls

- [[core-orchestrator-handlers-py-_action_from_context]]
- [[core-orchestrator-handlers-py-_append_operator_notice]]
