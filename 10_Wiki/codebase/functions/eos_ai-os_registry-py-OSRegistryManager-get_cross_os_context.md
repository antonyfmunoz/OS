---
type: codebase-function
file: eos_ai/os_registry.py
line: 276
generated: 2026-04-12
---

# OSRegistryManager.get_cross_os_context

**File:** [[eos_ai-os_registry-py]] | **Line:** 276
**Signature:** `get_cross_os_context(active_modules) → dict[str, list[str]]`

**Class:** [[eos_ai-os_registry-py-OSRegistryManager]]

Return shared context keys between active modules.
Only includes cross-OS data when BOTH sides are active.

## Called By

- [[eos_ai-os_registry-py-OSRegistryManager-format_for_prompt]]
