---
type: codebase-file
path: eos_ai/substrate/local_env_secret_backend.py
module: eos_ai.substrate.local_env_secret_backend
lines: 179
size: 5439
generated: 2026-05-07
---

# eos_ai/substrate/local_env_secret_backend.py

Local .env secret backend for Phase 94D.9S.

Development/bootstrap backend that reads secrets from a local .env file
outside the repository. The file must be at a safe path like
~/.umh/secrets/.env — never inside the repo.
...

**Lines:** 179 | **Size:** 5,439 bytes

## Depends On

- [[eos_ai-substrate-secret_broker_contracts-py]]

## Contains

- **fn** [[eos_ai-substrate-local_env_secret_backend-py-validate_env_path_is_outside_repo]]`(path, repo_root) → list[str]`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-reject_repo_env_files]]`(path, repo_root) → bool`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-_parse_env_lines]]`(lines) → dict[str, str]`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-load_env_file_keys_only]]`(path) → list[str]`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-has_secret]]`(path, key) → bool`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-get_secret_value_for_local_action]]`(path, key) → tuple[SecretUseStatus, str]`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-_infer_scope_from_key]]`(key) → SecretScope`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-build_secret_ref_from_key]]`(key, scope, account, path) → SecretRef`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-list_available_secret_refs]]`(path, account) → list[SecretRef]`
- **fn** [[eos_ai-substrate-local_env_secret_backend-py-build_secret_availability_report]]`(path) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from eos_ai.substrate.secret_broker_contracts import SecretBackendType
from eos_ai.substrate.secret_broker_contracts import SecretRef
from eos_ai.substrate.secret_broker_contracts import SecretScope
from eos_ai.substrate.secret_broker_contracts import SecretUseStatus
```
