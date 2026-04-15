---
type: codebase-function
file: eos_ai/os_trinity.py
line: 411
generated: 2026-04-12
---

# OSTrinity.register_product

**File:** [[eos_ai-os_trinity-py]] | **Line:** 411
**Signature:** `register_product(user_id, product, connection_config) → bool`

**Class:** [[eos_ai-os_trinity-py-OSTrinity]]

Register a product as connected for this user.
Safe to call repeatedly — does not create duplicates.
Returns True on success.
