---
type: codebase-class
file: eos_ai/os_registry.py
line: 242
generated: 2026-05-07
---

# OSRegistryManager

**File:** [[eos_ai-os_registry-py]] | **Line:** 242

Query and format the OS module registry.

Used by TrinityEngine to determine what context to inject
into the cognitive loop based on the user's subscriptions.

## Methods

- [[eos_ai-os_registry-py-OSRegistryManager-__init__]]`() → None` — 
- [[eos_ai-os_registry-py-OSRegistryManager-get_os]]`(module) → OSModuleConfig | None` — 
- [[eos_ai-os_registry-py-OSRegistryManager-get_active_modules]]`() → list[OSModuleConfig]` — Return all OS modules with status='active'.
- [[eos_ai-os_registry-py-OSRegistryManager-get_user_modules]]`(subscriptions) → list[OSModuleConfig]` — Return OS configs for the user's subscriptions.
- [[eos_ai-os_registry-py-OSRegistryManager-get_cross_os_context]]`(active_modules) → dict[str, list[str]]` — Return shared context keys between active modules.
- [[eos_ai-os_registry-py-OSRegistryManager-format_for_prompt]]`(subscriptions) → str` — Build the Layer 2 system prompt block for this user's subscriptions.
- [[eos_ai-os_registry-py-OSRegistryManager-get_all_modules]]`() → dict[OSModule, OSModuleConfig]` — 
