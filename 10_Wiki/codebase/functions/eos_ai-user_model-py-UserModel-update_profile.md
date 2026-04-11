---
type: codebase-function
file: eos_ai/user_model.py
line: 377
generated: 2026-04-11
---

# UserModel.update_profile

**File:** [[eos_ai-user_model-py]] | **Line:** 377
**Signature:** `update_profile() → dict`

**Class:** [[eos_ai-user_model-py-UserModel]]

Build communication profile and upsert to Neon user_profiles table.
Called automatically every 10 interactions via maybe_update_profile().
Returns the profile dict.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-user_model-py-UserModel-build_communication_profile]]

## Called By

- [[eos_ai-user_model-py-UserModel-maybe_update_profile]]
