---
type: codebase-file
path: eos_ai/substrate/execution_router.py
module: eos_ai.substrate.execution_router
lines: 220
size: 8124
generated: 2026-05-07
---

# eos_ai/substrate/execution_router.py

Data-driven execution router for the event-native execution fabric.

Stateless decision engine that accepts a RoutingContext and returns a
RoutingDecision. Consults the NodeRegistry for node health and capabilities.
NEVER invokes execution — only decides WHERE.
...

**Lines:** 220 | **Size:** 8,124 bytes

## Depends On

- [[eos_ai-substrate-execution_contract-py]]
- [[eos_ai-substrate-nodes-py]]

## Used By

- [[eos_ai-substrate-execution_authority-py]]

## Contains

- **class** [[eos_ai-substrate-execution_router-py-ExecutionRouter]] — 8 methods

## Import Statements

```python
from __future__ import annotations
from eos_ai.substrate.execution_contract import ExecutionClass
from eos_ai.substrate.execution_contract import ExecutionTarget
from eos_ai.substrate.execution_contract import RoutingContext
from eos_ai.substrate.execution_contract import RoutingDecision
from eos_ai.substrate.execution_contract import RoutingReasonCode
from eos_ai.substrate.nodes import Node
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeRole
from eos_ai.substrate.nodes import NodeStatus
```
