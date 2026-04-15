---
type: codebase-class
file: eos_ai/os_trinity.py
line: 39
generated: 2026-04-12
---

# OSTrinity

**File:** [[eos_ai-os_trinity-py]] | **Line:** 39

Harness-level data sharing, user intelligence, and product connection registry.

All methods are safe to call at any time — DB failures are caught and logged
without crashing the caller. Default for permission checks is always DENIED.

## Methods

- [[eos_ai-os_trinity-py-OSTrinity-__init__]]`(ctx) → None` — 
- [[eos_ai-os_trinity-py-OSTrinity-grant_permission]]`(user_id, source_product, target_product, data_category) → bool` — User explicitly grants target_product permission to read
- [[eos_ai-os_trinity-py-OSTrinity-revoke_permission]]`(user_id, source_product, target_product, data_category) → bool` — Revoke a previously granted permission.
- [[eos_ai-os_trinity-py-OSTrinity-check_permission]]`(user_id, source_product, target_product, data_category) → bool` — Returns True ONLY if an explicit, un-revoked permission exists.
- [[eos_ai-os_trinity-py-OSTrinity-get_user_permissions]]`(user_id) → list[dict]` — Return all permission records for this user (active and revoked).
- [[eos_ai-os_trinity-py-OSTrinity-update_intelligence_profile]]`(user_id, updates) → bool` — Upsert the harness-level user intelligence profile.
- [[eos_ai-os_trinity-py-OSTrinity-get_intelligence_profile]]`(user_id) → dict | None` — Load the harness-level intelligence profile for a user.
- [[eos_ai-os_trinity-py-OSTrinity-sync_from_user_model]]`(user_id) → bool` — Read the EOS-specific user_profiles row and promote relevant fields
- [[eos_ai-os_trinity-py-OSTrinity-register_product]]`(user_id, product, connection_config) → bool` — Register a product as connected for this user.
- [[eos_ai-os_trinity-py-OSTrinity-get_connected_products]]`(user_id) → list[str]` — Return list of product names currently connected for this user.
- [[eos_ai-os_trinity-py-OSTrinity-format_permissions_summary]]`(user_id) → str` — Human-readable OS Trinity status for Telegram /trinity command.
