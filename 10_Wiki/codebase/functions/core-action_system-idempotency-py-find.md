---
type: codebase-function
file: core/action_system/idempotency.py
line: 242
generated: 2026-04-12
---

# find

**File:** [[core-action_system-idempotency-py]] | **Line:** 242
**Signature:** `find(key_or_sha) → Sentinel | None`

Look up a sentinel by raw key OR by its sha1 filename prefix.

Operators use both forms — the full key when they know it, and the
sha prefix when copy-pasting from `list`.

## Calls

- [[core-action_system-idempotency-py-read]]
