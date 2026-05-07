---
type: codebase-file
path: eos_ai/substrate/secret_redaction.py
module: eos_ai.substrate.secret_redaction
lines: 112
size: 3161
generated: 2026-05-07
---

# eos_ai/substrate/secret_redaction.py

Secret redaction utilities for Phase 94D.9S.

Ensures secret values never appear in logs, messages, reports,
or model context. Provides pattern-based and value-based redaction.

...

**Lines:** 112 | **Size:** 3,161 bytes

## Depends On

- [[eos_ai-substrate-secret_broker_contracts-py]]

## Contains

- **fn** [[eos_ai-substrate-secret_redaction-py-looks_like_secret_key]]`(key) → bool`
- **fn** [[eos_ai-substrate-secret_redaction-py-redact_env_line]]`(line) → str`
- **fn** [[eos_ai-substrate-secret_redaction-py-redact_secret_values]]`(text, known_secret_values) → str`
- **fn** [[eos_ai-substrate-secret_redaction-py-redact_mapping]]`(mapping, secret_keys) → dict[str, Any]`
- **fn** [[eos_ai-substrate-secret_redaction-py-safe_repr_secret_ref]]`(secret_ref) → str`
- **fn** [[eos_ai-substrate-secret_redaction-py-redact_potential_secrets_in_output]]`(text) → str`

## Import Statements

```python
from __future__ import annotations
import re
from typing import Any
from eos_ai.substrate.secret_broker_contracts import SecretRef
```
