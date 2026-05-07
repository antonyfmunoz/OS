---
type: codebase-function
file: eos_ai/substrate/local_env_secret_backend.py
line: 137
generated: 2026-05-07
---

# build_secret_ref_from_key

**File:** [[eos_ai-substrate-local_env_secret_backend-py]] | **Line:** 137
**Signature:** `build_secret_ref_from_key(key, scope, account, path) → SecretRef`

Build a SecretRef from a key name. Never includes the value.

## Calls

- [[eos_ai-substrate-local_env_secret_backend-py-_infer_scope_from_key]]
- [[eos_ai-substrate-local_env_secret_backend-py-has_secret]]

## Called By

- [[eos_ai-substrate-local_env_secret_backend-py-list_available_secret_refs]]
