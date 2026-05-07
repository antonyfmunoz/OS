---
type: codebase-function
file: core/action_system/deferred_status.py
line: 80
generated: 2026-05-07
---

# write_status

**File:** [[core-action_system-deferred_status-py]] | **Line:** 80
**Signature:** `write_status(action_id, status) → DeferredStatus`

Persist a status sidecar for an action. Raises ValueError on bad status.

## Calls

- [[core-action_system-deferred_status-py-DeferredStatus-to_dict]]
- [[core-action_system-deferred_status-py-_status_path]]

## Called By

- [[core-action_system-deferred_status-py-mark_stale_over_threshold]]
- [[core-action_system-deferred_status-py-wake_due_snoozed]]
- [[scripts-deferred-py-cmd_status]]
