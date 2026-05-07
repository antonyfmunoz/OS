---
type: codebase-function
file: eos_ai/user_model.py
line: 100
generated: 2026-05-07
---

# UserModel.get_trust_level

**File:** [[eos_ai-user_model-py]] | **Line:** 100
**Signature:** `get_trust_level() → int`

**Class:** [[eos_ai-user_model-py-UserModel]]

Query total interaction count for this user/org.
Maps to trust level 1-5:
  0-9    → 1
  10-49  → 2
  50-99  → 3
...

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-user_model-py-UserModel-build_communication_profile]]
- [[eos_ai-user_model-py-UserModel-get_intent_expansion]]
