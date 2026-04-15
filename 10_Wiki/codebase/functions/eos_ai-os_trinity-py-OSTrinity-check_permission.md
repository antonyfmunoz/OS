---
type: codebase-function
file: eos_ai/os_trinity.py
line: 134
generated: 2026-04-12
---

# OSTrinity.check_permission

**File:** [[eos_ai-os_trinity-py]] | **Line:** 134
**Signature:** `check_permission(user_id, source_product, target_product, data_category) → bool`

**Class:** [[eos_ai-os_trinity-py-OSTrinity]]

Returns True ONLY if an explicit, un-revoked permission exists.
Default is always DENIED — no implicit cross-product data access.
