---
type: codebase-function
file: core/orchestrator/handlers.py
line: 150
generated: 2026-04-12
---

# handle_action_failed

**File:** [[core-orchestrator-handlers-py]] | **Line:** 150
**Signature:** `handle_action_failed(context) → dict[str, Any]`

React to a failed action that the loop already decided to escalate.

The loop only emits `action_failed` for actions it judged
NOT retry-eligible. The handler double-checks with
`should_ignore` / `should_escalate` so the rules live in exactly
...

## Calls

- [[core-orchestrator-handlers-py-_action_from_context]]
- [[core-orchestrator-handlers-py-_append_operator_notice]]
