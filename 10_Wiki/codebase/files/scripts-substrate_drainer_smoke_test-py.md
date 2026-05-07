---
type: codebase-file
path: scripts/substrate_drainer_smoke_test.py
module: scripts.substrate_drainer_smoke_test
lines: 123
size: 4286
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_drainer_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Substrate station drainer smoke test.

Proves the EOS-side ingestion seam end-to-end:

  1. Daemon-side: post a StationEvent via StationBus.daemon_post_event()
...

**Lines:** 123 | **Size:** 4,286 bytes

## Depends On

- [[eos_ai-event_bus-py]]
- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-station-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_drainer-py]]

## Contains

- **fn** [[scripts-substrate_drainer_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_drainer_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import time
from eos_ai.event_bus import EventBus
from eos_ai.substrate.actions import ActionResult
from eos_ai.substrate.actions import ActionStatus
from eos_ai.substrate.station import StationContract
from eos_ai.substrate.station import StationEvent
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_drainer import drain_node
```
