---
type: codebase-function
file: core/action_system/idempotency.py
line: 92
generated: 2026-04-12
---

# read

**File:** [[core-action_system-idempotency-py]] | **Line:** 92
**Signature:** `read(key) → Sentinel | None`

Return the current sentinel for a key, or None if absent.

## Calls

- [[core-action_system-idempotency-py-_path_for]]

## Called By

- [[core-action_system-idempotency-py-claim]]
- [[core-action_system-idempotency-py-complete]]
- [[core-action_system-idempotency-py-find]]
