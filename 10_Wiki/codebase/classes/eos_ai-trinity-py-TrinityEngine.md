---
type: codebase-class
file: eos_ai/trinity.py
line: 29
generated: 2026-04-12
---

# TrinityEngine

**File:** [[eos_ai-trinity-py]] | **Line:** 29

Determines which OS modules are active for the current user
and injects appropriate Layer 2 context into the cognitive loop.

Cross-OS insight fires only when 2+ modules are active.
Single-module users see standard module context only.

## Methods

- [[eos_ai-trinity-py-TrinityEngine-__init__]]`(ctx) → None` — 
- [[eos_ai-trinity-py-TrinityEngine-get_user_subscriptions]]`() → list[str]` — Load OS subscriptions from BIS.
- [[eos_ai-trinity-py-TrinityEngine-is_full_trinity]]`() → bool` — True when all three OS modules are active.
- [[eos_ai-trinity-py-TrinityEngine-get_active_os_count]]`() → int` — 
- [[eos_ai-trinity-py-TrinityEngine-get_cross_os_insight]]`(prompt) → str` — Detect when the prompt needs cross-OS context injection.
- [[eos_ai-trinity-py-TrinityEngine-format_for_prompt]]`() → str` — Build the Layer 2 system prompt block for this user.
