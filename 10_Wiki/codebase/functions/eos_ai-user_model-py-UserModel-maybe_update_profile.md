---
type: codebase-function
file: eos_ai/user_model.py
line: 439
generated: 2026-04-12
---

# UserModel.maybe_update_profile

**File:** [[eos_ai-user_model-py]] | **Line:** 439
**Signature:** `maybe_update_profile() → bool`

**Class:** [[eos_ai-user_model-py-UserModel]]

Check if interaction count hit a multiple of 10.
If so, trigger update_profile(). Returns True if profile was updated.
Called by CognitiveLoop after each interaction.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-user_model-py-UserModel-update_profile]]
