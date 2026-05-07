---
type: codebase-file
path: eos_ai/substrate/capability_routing_contracts.py
module: eos_ai.substrate.capability_routing_contracts
lines: 166
size: 5352
generated: 2026-05-07
---

# eos_ai/substrate/capability_routing_contracts.py

Capability-based routing contracts for Phase 94D.4.

Routes tasks to nodes based on capabilities, not node names.
A GUI computer-use task routes to a GUI-capable node.
Missing capability produces SETUP_REQUIRED, not hallucinated execution.

**Lines:** 166 | **Size:** 5,352 bytes

## Depends On

- [[eos_ai-substrate-topology_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-capability_routing_contracts-py-Capability]] — 0 methods
- **class** [[eos_ai-substrate-capability_routing_contracts-py-RoutingOutcome]] — 0 methods
- **class** [[eos_ai-substrate-capability_routing_contracts-py-RoutingRequirement]] — 1 methods
- **class** [[eos_ai-substrate-capability_routing_contracts-py-RoutingDecision]] — 1 methods
- **fn** [[eos_ai-substrate-capability_routing_contracts-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-capability_routing_contracts-py-score_node_for_requirement]]`(node, requirement) → tuple[float, list[str]]`
- **fn** [[eos_ai-substrate-capability_routing_contracts-py-choose_best_node]]`(topology, requirement) → RoutingDecision`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from eos_ai.substrate.topology_contracts import NodeProfile
from eos_ai.substrate.topology_contracts import TopologyProfile
```
