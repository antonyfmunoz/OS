---
type: codebase-function
file: core/action_system/deferred_status.py
line: 103
generated: 2026-04-12
---

# clear_status

**File:** [[core-action_system-deferred_status-py]] | **Line:** 103
**Signature:** `clear_status(action_id) → bool`

Remove the sidecar (used alongside delete_deferred on drop/approve).

## Calls

- [[core-action_system-deferred_status-py-_status_path]]

## Called By

- [[scripts-deferred-py-cmd_approve]]
- [[scripts-deferred-py-cmd_drop]]
- [[scripts-deferred-py-cmd_prune]]
