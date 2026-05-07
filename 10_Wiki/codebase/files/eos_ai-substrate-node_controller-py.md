---
type: codebase-file
path: eos_ai/substrate/node_controller.py
module: eos_ai.substrate.node_controller
lines: 357
size: 13468
generated: 2026-05-07
---

# eos_ai/substrate/node_controller.py

NodeController — unified routing brain for task→node dispatch.

Single decision engine that consolidates task-to-node routing.
Stateless: every call re-reads current state from the existing
singletons (NodeRegistry, StationPresenceStore, OperatorSessionStore).
...

**Lines:** 357 | **Size:** 13,468 bytes

## Contains

- **class** [[eos_ai-substrate-node_controller-py-TransportPreference]] — 0 methods
- **class** [[eos_ai-substrate-node_controller-py-RoutingReason]] — 0 methods
- **class** [[eos_ai-substrate-node_controller-py-RoutingDecision]] — 1 methods
- **fn** [[eos_ai-substrate-node_controller-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-node_controller-py-_is_local_node_online]]`() → bool`
- **fn** [[eos_ai-substrate-node_controller-py-_is_http_transport_available]]`() → bool`
- **fn** [[eos_ai-substrate-node_controller-py-_is_local_available_via_presence]]`() → bool`
- **fn** [[eos_ai-substrate-node_controller-py-get_node_health_summary]]`() → dict`
- **fn** [[eos_ai-substrate-node_controller-py-route]]`() → RoutingDecision`
- **fn** [[eos_ai-substrate-node_controller-py-_local_decision]]`(http_up, reason, detail) → RoutingDecision`
- **fn** [[eos_ai-substrate-node_controller-py-_vps_decision]]`(reason, detail) → RoutingDecision`

## Import Statements

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING
from typing import Optional
```
