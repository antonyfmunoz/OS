---
type: codebase-function
file: core/action_system/idempotency.py
line: 273
generated: 2026-04-12
---

# prune_expired

**File:** [[core-action_system-idempotency-py]] | **Line:** 273
**Signature:** `prune_expired() → list[str]`

Remove every expired sentinel. Returns list of cleared keys.

## Calls

- [[core-action_system-idempotency-py-Sentinel-is_expired]]
- [[core-action_system-idempotency-py-clear]]
- [[core-action_system-idempotency-py-list_all]]
