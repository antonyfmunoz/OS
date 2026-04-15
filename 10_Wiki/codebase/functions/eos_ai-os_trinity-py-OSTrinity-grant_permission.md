---
type: codebase-function
file: eos_ai/os_trinity.py
line: 52
generated: 2026-04-12
---

# OSTrinity.grant_permission

**File:** [[eos_ai-os_trinity-py]] | **Line:** 52
**Signature:** `grant_permission(user_id, source_product, target_product, data_category) → bool`

**Class:** [[eos_ai-os_trinity-py-OSTrinity]]

User explicitly grants target_product permission to read
source_product data in data_category.

Upserts to cross_product_permissions. Clears revoked_at on re-grant.
Returns True on success.
