---
type: codebase-function
file: eos_ai/os_registry.py
line: 294
generated: 2026-05-07
---

# OSRegistryManager.format_for_prompt

**File:** [[eos_ai-os_registry-py]] | **Line:** 294
**Signature:** `format_for_prompt(subscriptions) → str`

**Class:** [[eos_ai-os_registry-py-OSRegistryManager]]

Build the Layer 2 system prompt block for this user's subscriptions.
Returns empty string if no subscriptions matched.

## Calls

- [[eos_ai-os_registry-py-OSRegistryManager-get_cross_os_context]]
- [[eos_ai-os_registry-py-OSRegistryManager-get_user_modules]]

## Called By

- [[eos_ai-trinity-py-TrinityEngine-format_for_prompt]]
