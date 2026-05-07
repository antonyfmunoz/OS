---
type: codebase-function
file: eos_ai/substrate/local_env_secret_backend.py
line: 79
generated: 2026-05-07
---

# load_env_file_keys_only

**File:** [[eos_ai-substrate-local_env_secret_backend-py]] | **Line:** 79
**Signature:** `load_env_file_keys_only(path) → list[str]`

Load only the KEY names from a .env file. Never returns values.

## Calls

- [[eos_ai-substrate-local_env_secret_backend-py-_parse_env_lines]]
- [[eos_ai-substrate-local_env_secret_backend-py-validate_env_path_is_outside_repo]]

## Called By

- [[eos_ai-substrate-local_env_secret_backend-py-build_secret_availability_report]]
- [[eos_ai-substrate-local_env_secret_backend-py-has_secret]]
- [[eos_ai-substrate-local_env_secret_backend-py-list_available_secret_refs]]
