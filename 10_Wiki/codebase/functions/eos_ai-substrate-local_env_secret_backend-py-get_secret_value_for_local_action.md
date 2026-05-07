---
type: codebase-function
file: eos_ai/substrate/local_env_secret_backend.py
line: 101
generated: 2026-05-07
---

# get_secret_value_for_local_action

**File:** [[eos_ai-substrate-local_env_secret_backend-py]] | **Line:** 101
**Signature:** `get_secret_value_for_local_action(path, key) → tuple[SecretUseStatus, str]`

Retrieve a secret value for use in an approved local action.

WARNING: This function returns the actual secret value.
It must ONLY be called inside approved deterministic action execution.
The return value must NEVER be printed, logged, sent to model context,
...

## Calls

- [[eos_ai-substrate-local_env_secret_backend-py-_parse_env_lines]]
- [[eos_ai-substrate-local_env_secret_backend-py-validate_env_path_is_outside_repo]]
