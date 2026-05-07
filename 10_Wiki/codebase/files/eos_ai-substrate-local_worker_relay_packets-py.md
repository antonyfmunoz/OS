---
type: codebase-file
path: eos_ai/substrate/local_worker_relay_packets.py
module: eos_ai.substrate.local_worker_relay_packets
lines: 200
size: 7540
generated: 2026-05-07
---

# eos_ai/substrate/local_worker_relay_packets.py

Local worker relay packets for Phase 94D.5.

Generates the auto-mode worker instruction packet for W0-001 and
other work orders dispatched to the local PC worker.

...

**Lines:** 200 | **Size:** 7,540 bytes

## Depends On

- [[eos_ai-substrate-computer_use_backend_contracts-py]]
- [[eos_ai-substrate-governance_gate_contracts-py]]
- [[eos_ai-substrate-worker_node_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-local_worker_relay_packets-py-WorkerRelayPacket]] — 4 methods
- **fn** [[eos_ai-substrate-local_worker_relay_packets-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-local_worker_relay_packets-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-local_worker_relay_packets-py-build_wo_001_relay_packet]]`() → WorkerRelayPacket`
- **fn** [[eos_ai-substrate-local_worker_relay_packets-py-validate_relay_packet]]`(packet) → list[str]`

## Import Statements

```python
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from eos_ai.substrate.computer_use_backend_contracts import ComputerUseBackend
from eos_ai.substrate.governance_gate_contracts import ALWAYS_BLOCKED_ACTIONS
from eos_ai.substrate.worker_node_contracts import WorkerMode
```
