---
type: codebase-file
path: eos_ai/substrate/topology_contracts.py
module: eos_ai.substrate.topology_contracts
lines: 264
size: 7833
generated: 2026-05-07
---

# eos_ai/substrate/topology_contracts.py

Setup-agnostic topology contracts for Phase 94D.4.

Defines topology, node, interface, and transport profiles that support
arbitrary user setups — not just the founder's VPS + local PC topology.

...

**Lines:** 264 | **Size:** 7,833 bytes

## Used By

- [[eos_ai-substrate-capability_routing_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-topology_contracts-py-NodeType]] — 0 methods
- **class** [[eos_ai-substrate-topology_contracts-py-NodeRole]] — 0 methods
- **class** [[eos_ai-substrate-topology_contracts-py-InterfaceRole]] — 0 methods
- **class** [[eos_ai-substrate-topology_contracts-py-TransportType]] — 0 methods
- **class** [[eos_ai-substrate-topology_contracts-py-TransportProfile]] — 1 methods
- **class** [[eos_ai-substrate-topology_contracts-py-InterfaceProfile]] — 1 methods
- **class** [[eos_ai-substrate-topology_contracts-py-NodeProfile]] — 4 methods
- **class** [[eos_ai-substrate-topology_contracts-py-TopologyProfile]] — 5 methods
- **fn** [[eos_ai-substrate-topology_contracts-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-topology_contracts-py-build_founder_current_topology]]`() → TopologyProfile`
- **fn** [[eos_ai-substrate-topology_contracts-py-build_single_local_topology]]`(owner_id) → TopologyProfile`

## Import Statements

```python
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
