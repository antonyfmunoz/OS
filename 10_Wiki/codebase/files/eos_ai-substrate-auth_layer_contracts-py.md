---
type: codebase-file
path: eos_ai/substrate/auth_layer_contracts.py
module: eos_ai.substrate.auth_layer_contracts
lines: 90
size: 3077
generated: 2026-05-07
---

# eos_ai/substrate/auth_layer_contracts.py

Auth layer contracts for Phase 96.3.

OAuth is authorization, not backend.
Browser profile session is authorization/session context, not backend.
Secret values never enter model context.
...

**Lines:** 90 | **Size:** 3,077 bytes

## Contains

- **class** [[eos_ai-substrate-auth_layer_contracts-py-AuthMethodType]] — 0 methods
- **class** [[eos_ai-substrate-auth_layer_contracts-py-AuthMaterialHandling]] — 0 methods
- **class** [[eos_ai-substrate-auth_layer_contracts-py-AuthProfile]] — 1 methods
- **fn** [[eos_ai-substrate-auth_layer_contracts-py-is_auth_not_backend]]`(method) → bool`
- **fn** [[eos_ai-substrate-auth_layer_contracts-py-is_browser_profile_auth_not_backend]]`(method) → bool`
- **fn** [[eos_ai-substrate-auth_layer_contracts-py-secret_must_not_enter_model_context]]`() → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
