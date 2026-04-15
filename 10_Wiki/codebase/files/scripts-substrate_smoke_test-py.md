---
type: codebase-file
path: scripts/substrate_smoke_test.py
module: scripts.substrate_smoke_test
lines: 228
size: 9210
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Substrate station MVP smoke test.

Proves the smallest real end-to-end loop:
  1. Daemon registers as a node and emits a heartbeat.
  2. EOS side proposes SPEAK_TEXT + PLAY_SOUND via StationContract.
...

**Lines:** 228 | **Size:** 9,210 bytes

## Depends On

- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-ritual_runner-py]]
- [[eos_ai-substrate-rituals-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_helpers-py]]

## Contains

- **fn** [[scripts-substrate_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
import time
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.ritual_body import RitualPolicy
from eos_ai.substrate.ritual_runner import start_close_day
from eos_ai.substrate.ritual_runner import start_open_day
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.station_helpers import propose_open_scene
from eos_ai.substrate.station_helpers import propose_open_url
from eos_ai.substrate.station_helpers import propose_launch_app
from eos_ai.substrate.station_helpers import propose_play_sound
from eos_ai.substrate.station_helpers import propose_speak_text
```
