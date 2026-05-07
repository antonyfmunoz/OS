---
type: codebase-file
path: eos_ai/substrate/execution_contract.py
module: eos_ai.substrate.execution_contract
lines: 303
size: 9950
generated: 2026-05-07
---

# eos_ai/substrate/execution_contract.py

Execution contract types for the event-native execution fabric.

Platform-agnostic, frozen, JSON-serializable data contracts that define
the boundary between the control plane (decides what runs) and the
execution plane (runs it).
...

**Lines:** 303 | **Size:** 9,950 bytes

## Used By

- [[eos_ai-substrate-execution_adapter-py]]
- [[eos_ai-substrate-execution_authority-py]]
- [[eos_ai-substrate-execution_events-py]]
- [[eos_ai-substrate-execution_result_handler-py]]
- [[eos_ai-substrate-execution_router-py]]
- [[eos_ai-substrate-execution_worker-py]]

## Contains

- **class** [[eos_ai-substrate-execution_contract-py-ExecutionClass]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-ExecutionStatus]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-RoutingReasonCode]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-ExecutionConstraints]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-NodeCapability]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-NodeHealthSnapshot]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-ExecutionTarget]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-RoutingContext]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-RoutingDecision]] — 0 methods
- **class** [[eos_ai-substrate-execution_contract-py-ExecutionRequest]] — 2 methods
- **class** [[eos_ai-substrate-execution_contract-py-ExecutionResult]] — 2 methods
- **fn** [[eos_ai-substrate-execution_contract-py-_new_execution_id]]`() → str`
- **fn** [[eos_ai-substrate-execution_contract-py-_compute_idempotency_key]]`(primitive_name, inputs) → str`
- **fn** [[eos_ai-substrate-execution_contract-py-_compute_execution_hash]]`(execution_id, status, outputs) → str`

## Import Statements

```python
from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Optional
```
