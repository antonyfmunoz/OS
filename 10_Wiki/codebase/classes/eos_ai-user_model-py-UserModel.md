---
type: codebase-class
file: eos_ai/user_model.py
line: 57
generated: 2026-05-07
---

# UserModel

**File:** [[eos_ai-user_model-py]] | **Line:** 57

Behavioral model of the founder's communication style, decision patterns,
and compressed vocabulary.

Updated every 10 interactions (via maybe_update_profile()).
Used by CognitiveLoop._enhance_prompt() to expand vague instructions
...

## Methods

- [[eos_ai-user_model-py-UserModel-__init__]]`(ctx)` — 
- [[eos_ai-user_model-py-UserModel-_ensure_table]]`() → None` — Create user_profiles table in Neon if it does not exist.
- [[eos_ai-user_model-py-UserModel-get_trust_level]]`() → int` — Query total interaction count for this user/org.
- [[eos_ai-user_model-py-UserModel-build_communication_profile]]`() → dict` — Query last 30 days of interactions from Neon. Analyze input_summary
- [[eos_ai-user_model-py-UserModel-get_intent_expansion]]`(raw_prompt) → str` — If a profile exists and trust_level >= 3, use it to expand compressed
- [[eos_ai-user_model-py-UserModel-update_profile]]`() → dict` — Build communication profile and upsert to Neon user_profiles table.
- [[eos_ai-user_model-py-UserModel-_load_profile]]`() → dict | None` — Load stored profile from Neon. Returns None if not found.
- [[eos_ai-user_model-py-UserModel-maybe_update_profile]]`() → bool` — Check if interaction count hit a multiple of 10.
