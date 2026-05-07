---
type: codebase-file
path: eos_ai/substrate/capabilities.py
module: eos_ai.substrate.capabilities
lines: 81
size: 2822
generated: 2026-05-07
---

# eos_ai/substrate/capabilities.py

Capability abstraction — what a node can do.

Future routing should target *capabilities*, not machines. Today the VPS is
the only executor; tomorrow a local Station Daemon will advertise things the
VPS cannot do (microphone input, screen inspection, full computer control).
...

**Lines:** 81 | **Size:** 2,822 bytes

## Used By

- [[eos_ai-substrate-capability_tagging-py]]
- [[eos_ai-substrate-scene_capabilities-py]]

## Contains

- **class** [[eos_ai-substrate-capabilities-py-Capability]] — 1 methods
- **class** [[eos_ai-substrate-capabilities-py-CapabilityRegistry]] — 4 methods

## Import Statements

```python
from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING
```
