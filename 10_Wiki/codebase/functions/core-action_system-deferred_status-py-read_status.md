---
type: codebase-function
file: core/action_system/deferred_status.py
line: 63
generated: 2026-04-12
---

# read_status

**File:** [[core-action_system-deferred_status-py]] | **Line:** 63
**Signature:** `read_status(action_id) → DeferredStatus`

Return the sidecar status for a deferred action, or the pending default.

## Calls

- [[core-action_system-deferred_status-py-_status_path]]

## Called By

- [[core-action_system-deferred_status-py-list_overdue_snoozed]]
- [[core-action_system-deferred_status-py-mark_stale_over_threshold]]
- [[core-action_system-deferred_status-py-wake_due_snoozed]]
- [[scripts-deferred-py-cmd_list]]
- [[scripts-deferred-py-cmd_prune]]
- [[scripts-deferred-py-cmd_status]]
