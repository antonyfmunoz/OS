---
type: codebase-function
file: eos_ai/substrate/local_env_secret_backend.py
line: 42
generated: 2026-05-07
---

# validate_env_path_is_outside_repo

**File:** [[eos_ai-substrate-local_env_secret_backend-py]] | **Line:** 42
**Signature:** `validate_env_path_is_outside_repo(path, repo_root) → list[str]`

Validate that the secret .env path is outside the repository.

## Called By

- [[eos_ai-substrate-local_env_secret_backend-py-get_secret_value_for_local_action]]
- [[eos_ai-substrate-local_env_secret_backend-py-load_env_file_keys_only]]
- [[eos_ai-substrate-local_env_secret_backend-py-reject_repo_env_files]]
