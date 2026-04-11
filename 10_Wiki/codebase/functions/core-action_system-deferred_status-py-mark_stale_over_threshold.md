---
type: codebase-function
file: core/action_system/deferred_status.py
line: 203
generated: 2026-04-11
---

# mark_stale_over_threshold

**File:** [[core-action_system-deferred_status-py]] | **Line:** 203
**Signature:** `mark_stale_over_threshold(threshold_hours) → list[str]`

Scan the deferred queue and mark actions past the threshold as stale.

Returns the list of action ids newly marked stale. Skips actions
already in a non-pending status so operator annotations are not
clobbered.

## Calls

- [[core-action_system-deferred_status-py-is_stale]]
- [[core-action_system-deferred_status-py-read_status]]
- [[core-action_system-deferred_status-py-write_status]]

## Called By

- [[scripts-deferred-py-cmd_prune]]
- [[scripts-deferred-py-cmd_stale_check]]
