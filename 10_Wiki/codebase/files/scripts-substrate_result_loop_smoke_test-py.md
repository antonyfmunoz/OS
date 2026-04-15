---
type: codebase-file
path: scripts/substrate_result_loop_smoke_test.py
module: scripts.substrate_result_loop_smoke_test
lines: 161
size: 6511
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_result_loop_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Substrate station full round-trip smoke test.

Proves the result/ritual loop end-to-end:

  1. Ritual body (open_day) proposes SPEAK_TEXT + OPEN_SCENE via the station
...

**Lines:** 161 | **Size:** 6,511 bytes

## Depends On

- [[eos_ai-substrate-result_store-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-ritual_reconciler-py]]
- [[eos_ai-substrate-ritual_runner-py]]
- [[eos_ai-substrate-rituals-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_drainer-py]]
- [[eos_ai-substrate-station_helpers-py]]

## Contains

- **fn** [[scripts-substrate_result_loop_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_result_loop_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.result_store import get_result_store
from eos_ai.substrate.result_store import reset_result_store_for_tests
from eos_ai.substrate.ritual_body import RitualPolicy
from eos_ai.substrate.ritual_reconciler import reconcile_ritual
from eos_ai.substrate.ritual_runner import start_open_day
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.station_drainer import drain_all
from eos_ai.substrate.station_helpers import propose_focus_app
```
