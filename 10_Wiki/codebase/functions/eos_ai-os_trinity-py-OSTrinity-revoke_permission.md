---
type: codebase-function
file: eos_ai/os_trinity.py
line: 96
generated: 2026-04-11
---

# OSTrinity.revoke_permission

**File:** [[eos_ai-os_trinity-py]] | **Line:** 96
**Signature:** `revoke_permission(user_id, source_product, target_product, data_category) → bool`

**Class:** [[eos_ai-os_trinity-py-OSTrinity]]

Revoke a previously granted permission.
Sets permitted=false and stamps revoked_at.
Returns True on success.
