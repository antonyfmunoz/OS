---
type: codebase-function
file: eos_ai/os_trinity.py
line: 202
generated: 2026-04-11
---

# OSTrinity.update_intelligence_profile

**File:** [[eos_ai-os_trinity-py]] | **Line:** 202
**Signature:** `update_intelligence_profile(user_id, updates) → bool`

**Class:** [[eos_ai-os_trinity-py-OSTrinity]]

Upsert the harness-level user intelligence profile.

Only fields present in `updates` are written — all others are
preserved. JSONB fields are fully replaced when included; scalars
(north_star) are replaced directly.
...

## Called By

- [[eos_ai-os_trinity-py-OSTrinity-sync_from_user_model]]
