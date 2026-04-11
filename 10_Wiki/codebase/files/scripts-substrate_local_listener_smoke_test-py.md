---
type: codebase-file
path: scripts/substrate_local_listener_smoke_test.py
module: scripts.substrate_local_listener_smoke_test
lines: 147
size: 5700
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_local_listener_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Local listener smoke test.

Proves the smallest real end-to-end activation flow:
  1. A node is registered + heartbeated via StationDaemon (so readiness is fresh).
  2. LocalListener.manual_activate(...) emits a bounded trigger.
...

**Lines:** 147 | **Size:** 5,700 bytes

## Depends On

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-rituals-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]

## Contains

- **fn** [[scripts-substrate_local_listener_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_local_listener_smoke_test-py-_fail_terminal_open_days]]`() → None`
- **fn** [[scripts-substrate_local_listener_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.local_listener import LocalListener
from eos_ai.substrate.local_listener import LocalTrigger
from eos_ai.substrate.local_listener import TriggerKind
from eos_ai.substrate.local_listener import TriggerStatus
from eos_ai.substrate.local_listener import get_trigger_history
from eos_ai.substrate.local_listener import listener_report
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.rituals import RitualKind
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
```
