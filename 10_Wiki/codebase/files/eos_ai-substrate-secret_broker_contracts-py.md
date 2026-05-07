---
type: codebase-file
path: eos_ai/substrate/secret_broker_contracts.py
module: eos_ai.substrate.secret_broker_contracts
lines: 213
size: 6320
generated: 2026-05-07
---

# eos_ai/substrate/secret_broker_contracts.py

Secret broker contracts for Phase 94D.9S.

Defines the abstraction layer for secret management.
Secrets are protected resources used by approved deterministic actions.
The model/advisor never sees secret values.
...

**Lines:** 213 | **Size:** 6,320 bytes

## Used By

- [[eos_ai-substrate-local_env_secret_backend-py]]
- [[eos_ai-substrate-secret_redaction-py]]

## Contains

- **class** [[eos_ai-substrate-secret_broker_contracts-py-SecretScope]] — 0 methods
- **class** [[eos_ai-substrate-secret_broker_contracts-py-SecretBackendType]] — 0 methods
- **class** [[eos_ai-substrate-secret_broker_contracts-py-SecretUseStatus]] — 0 methods
- **class** [[eos_ai-substrate-secret_broker_contracts-py-SecretRef]] — 3 methods
- **class** [[eos_ai-substrate-secret_broker_contracts-py-SecretUseRequest]] — 2 methods
- **class** [[eos_ai-substrate-secret_broker_contracts-py-SecretUseGrant]] — 3 methods
- **class** [[eos_ai-substrate-secret_broker_contracts-py-SecretUseAuditEvent]] — 2 methods
- **fn** [[eos_ai-substrate-secret_broker_contracts-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-secret_broker_contracts-py-validate_secret_use_request]]`(request) → list[str]`
- **fn** [[eos_ai-substrate-secret_broker_contracts-py-validate_secret_use_grant]]`(grant) → list[str]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
