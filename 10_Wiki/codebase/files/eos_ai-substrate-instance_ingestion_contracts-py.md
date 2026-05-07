---
type: codebase-file
path: eos_ai/substrate/instance_ingestion_contracts.py
module: eos_ai.substrate.instance_ingestion_contracts
lines: 66
size: 2297
generated: 2026-05-07
---

# eos_ai/substrate/instance_ingestion_contracts.py

Instance ingestion contracts for Phase 96.4.

W0-001 data is instance-specific to Antony / Empyrean.
Instance source data defaults to INSTANCE_MEMORY scope.
Global canon not allowed by default for user account data.

**Lines:** 66 | **Size:** 2,297 bytes

## Depends On

- [[eos_ai-substrate-memory_scope_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-instance_ingestion_contracts-py-InstanceSourceContext]] — 1 methods
- **fn** [[eos_ai-substrate-instance_ingestion_contracts-py-build_w0_001_instance_context]]`() → InstanceSourceContext`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from eos_ai.substrate.memory_scope_contracts import MemoryScope
```
