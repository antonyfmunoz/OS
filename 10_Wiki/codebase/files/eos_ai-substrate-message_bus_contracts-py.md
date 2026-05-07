---
type: codebase-file
path: eos_ai/substrate/message_bus_contracts.py
module: eos_ai.substrate.message_bus_contracts
lines: 215
size: 6351
generated: 2026-05-07
---

# eos_ai/substrate/message_bus_contracts.py

Message bus contracts for Phase 94D.3.

Additive-only module. Defines the interface-agnostic message envelope,
message types, source interfaces, and serialization helpers.

...

**Lines:** 215 | **Size:** 6,351 bytes

## Used By

- [[eos_ai-substrate-advisor_bridge_transport-py]]
- [[eos_ai-substrate-advisor_relay_runtime-py]]
- [[eos_ai-substrate-worker_node_runtime-py]]

## Contains

- **class** [[eos_ai-substrate-message_bus_contracts-py-MessageType]] — 0 methods
- **class** [[eos_ai-substrate-message_bus_contracts-py-SourceInterface]] — 0 methods
- **class** [[eos_ai-substrate-message_bus_contracts-py-MessagePriority]] — 0 methods
- **class** [[eos_ai-substrate-message_bus_contracts-py-MessageStatus]] — 0 methods
- **class** [[eos_ai-substrate-message_bus_contracts-py-MessageEnvelope]] — 4 methods
- **fn** [[eos_ai-substrate-message_bus_contracts-py-_new_message_id]]`() → str`
- **fn** [[eos_ai-substrate-message_bus_contracts-py-_now_iso]]`() → str`

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
