---
type: codebase-function
file: eos_ai/user_model.py
line: 320
generated: 2026-05-07
---

# UserModel.get_intent_expansion

**File:** [[eos_ai-user_model-py]] | **Line:** 320
**Signature:** `get_intent_expansion(raw_prompt) → str`

**Class:** [[eos_ai-user_model-py-UserModel]]

If a profile exists and trust_level >= 3, use it to expand compressed
prompts into their full intent. Routes through Haiku (fast, cheap).

e.g. "do outreach" → "Run the daily Instagram DM outreach sequence for
Initiate Arena ICP segment using the warm opener template. Focus on
...

## Calls

- [[eos_ai-user_model-py-UserModel-_load_profile]]
- [[eos_ai-user_model-py-UserModel-get_trust_level]]
