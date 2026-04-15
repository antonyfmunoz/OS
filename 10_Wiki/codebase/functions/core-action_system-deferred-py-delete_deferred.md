---
type: codebase-function
file: core/action_system/deferred.py
line: 53
generated: 2026-04-12
---

# delete_deferred

**File:** [[core-action_system-deferred-py]] | **Line:** 53
**Signature:** `delete_deferred(action_id) → bool`

Remove the deferred file. Returns True if removed, False if not present.

## Calls

- [[core-action_system-deferred-py-_path_for]]

## Called By

- [[scripts-deferred-py-cmd_drop]]
- [[scripts-deferred-py-cmd_prune]]
