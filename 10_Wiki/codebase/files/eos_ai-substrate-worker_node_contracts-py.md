---
type: codebase-file
path: eos_ai/substrate/worker_node_contracts.py
module: eos_ai.substrate.worker_node_contracts
lines: 207
size: 6333
generated: 2026-05-07
---

# eos_ai/substrate/worker_node_contracts.py

Worker node organism contracts for Phase 94D.4.

Defines worker modes, states, profiles, and event types for execution
nodes that operate like organism cells — perceive, plan, execute, observe,
report, emit feedback.
...

**Lines:** 207 | **Size:** 6,333 bytes

## Used By

- [[eos_ai-substrate-advisor_relay_runtime-py]]
- [[eos_ai-substrate-local_worker_relay_packets-py]]
- [[eos_ai-substrate-worker_node_runtime-py]]

## Contains

- **class** [[eos_ai-substrate-worker_node_contracts-py-WorkerMode]] — 0 methods
- **class** [[eos_ai-substrate-worker_node_contracts-py-WorkerState]] — 0 methods
- **class** [[eos_ai-substrate-worker_node_contracts-py-WorkerRole]] — 0 methods
- **class** [[eos_ai-substrate-worker_node_contracts-py-WorkerProfile]] — 3 methods
- **class** [[eos_ai-substrate-worker_node_contracts-py-WorkerRuntimeState]] — 3 methods
- **class** [[eos_ai-substrate-worker_node_contracts-py-WorkerAction]] — 1 methods
- **class** [[eos_ai-substrate-worker_node_contracts-py-WorkerFeedbackEvent]] — 2 methods
- **fn** [[eos_ai-substrate-worker_node_contracts-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-worker_node_contracts-py-_new_id]]`() → str`

## Import Statements

```python
from __future__ import annotations
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
