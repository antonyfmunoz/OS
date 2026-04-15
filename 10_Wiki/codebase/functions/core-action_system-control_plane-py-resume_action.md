---
type: codebase-function
file: core/action_system/control_plane.py
line: 221
generated: 2026-04-12
---

# resume_action

**File:** [[core-action_system-control_plane-py]] | **Line:** 221
**Signature:** `resume_action(action_id) → Action`

Approve and execute a previously-deferred action by id.

Loads the persisted action, grants explicit approval, runs the
executor, logs the full transition trail, and deletes the deferred
file on any terminal state (executed or failed). If the action
...

## Calls

- [[core-action_system-control_plane-py-_execute_approved]]

## Called By

- [[scripts-deferred-py-cmd_approve]]
