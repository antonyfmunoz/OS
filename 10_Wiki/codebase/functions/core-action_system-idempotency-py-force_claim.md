---
type: codebase-function
file: core/action_system/idempotency.py
line: 168
generated: 2026-05-07
---

# force_claim

**File:** [[core-action_system-idempotency-py]] | **Line:** 168
**Signature:** `force_claim(key, action_id, ttl_seconds) → Sentinel`

Overwrite any existing sentinel for `key` with a fresh in_flight claim.

Used by the control_plane when the prior sentinel is expired, failed,
or points at a deferred action whose file has been dropped.

## Calls

- [[core-action_system-idempotency-py-_now_iso]]
- [[core-action_system-idempotency-py-_write]]
