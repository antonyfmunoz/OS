---
type: codebase-function
file: core/action_system/idempotency.py
line: 120
generated: 2026-04-12
---

# claim

**File:** [[core-action_system-idempotency-py]] | **Line:** 120
**Signature:** `claim(key, action_id, ttl_seconds) → tuple[bool, Sentinel]`

Attempt to atomically claim `key` for `action_id`.

Returns (won, sentinel):
  - (True,  new_sentinel)       — we created it; caller proceeds.
  - (False, existing_sentinel)  — someone else holds it; caller inspects status.
...

## Calls

- [[core-action_system-idempotency-py-Sentinel-to_dict]]
- [[core-action_system-idempotency-py-_now_iso]]
- [[core-action_system-idempotency-py-_path_for]]
- [[core-action_system-idempotency-py-read]]
