---
type: codebase-function
file: core/action_system/idempotency.py
line: 214
generated: 2026-05-07
---

# list_all

**File:** [[core-action_system-idempotency-py]] | **Line:** 214
**Signature:** `list_all() → list[Sentinel]`

Return every sentinel on disk. Sorted by created_at descending.

## Called By

- [[core-action_system-idempotency-py-prune_expired]]
