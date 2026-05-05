---
type: codebase-function
file: core/action_system/idempotency.py
line: 204
generated: 2026-04-12
---

# clear

**File:** [[core-action_system-idempotency-py]] | **Line:** 204
**Signature:** `clear(key) → bool`

Delete the sentinel for `key`. Returns True if removed.

## Calls

- [[core-action_system-idempotency-py-_path_for]]

## Called By

- [[core-action_system-idempotency-py-prune_expired]]
