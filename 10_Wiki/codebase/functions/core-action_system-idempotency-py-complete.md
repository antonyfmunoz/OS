---
type: codebase-function
file: core/action_system/idempotency.py
line: 186
generated: 2026-05-07
---

# complete

**File:** [[core-action_system-idempotency-py]] | **Line:** 186
**Signature:** `complete(key, status) → Sentinel | None`

Update the sentinel for `key` to a terminal or intermediate status.

Valid statuses: executed | failed | deferred.
Returns the updated sentinel, or None if the sentinel is missing.

## Calls

- [[core-action_system-idempotency-py-_now_iso]]
- [[core-action_system-idempotency-py-_write]]
- [[core-action_system-idempotency-py-read]]
