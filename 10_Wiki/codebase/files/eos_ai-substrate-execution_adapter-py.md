---
type: codebase-file
path: eos_ai/substrate/execution_adapter.py
module: eos_ai.substrate.execution_adapter
lines: 416
size: 13719
generated: 2026-05-07
---

# eos_ai/substrate/execution_adapter.py

Execution adapters — stateless wrappers around existing execution code.

Each adapter translates between the ExecutionRequest/ExecutionResult contract
and an underlying executor (local_executor, node_transport, etc.).

...

**Lines:** 416 | **Size:** 13,719 bytes

## Depends On

- [[eos_ai-substrate-control_commands-py]]
- [[eos_ai-substrate-execution_contract-py]]

## Used By

- [[eos_ai-substrate-execution_worker-py]]

## Contains

- **class** [[eos_ai-substrate-execution_adapter-py-ExecutionAdapter]] — 5 methods
- **class** [[eos_ai-substrate-execution_adapter-py-AdapterHealth]] — 0 methods
- **class** [[eos_ai-substrate-execution_adapter-py-LocalRuntimeAdapter]] — 6 methods
- **class** [[eos_ai-substrate-execution_adapter-py-WorkstationAdapter]] — 6 methods
- **fn** [[eos_ai-substrate-execution_adapter-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-execution_adapter-py-_iso_now]]`() → str`
- **fn** [[eos_ai-substrate-execution_adapter-py-_make_result]]`(request) → ExecutionResult`

## Import Statements

```python
from __future__ import annotations
import asyncio
import sys
import time
from dataclasses import dataclass
from typing import Any
from typing import Protocol
from eos_ai.substrate.control_commands import ControlCommand
from eos_ai.substrate.execution_contract import ExecutionRequest
from eos_ai.substrate.execution_contract import ExecutionResult
from eos_ai.substrate.execution_contract import ExecutionStatus
```
