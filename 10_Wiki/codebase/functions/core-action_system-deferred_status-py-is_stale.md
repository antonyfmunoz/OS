---
type: codebase-function
file: core/action_system/deferred_status.py
line: 112
generated: 2026-05-07
---

# is_stale

**File:** [[core-action_system-deferred_status-py]] | **Line:** 112
**Signature:** `is_stale(deferred_at) → bool`

Return True if the given ISO timestamp is older than the threshold.

## Called By

- [[core-action_system-deferred_status-py-mark_stale_over_threshold]]
