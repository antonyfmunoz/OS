---
type: codebase-file
path: scripts/substrate_drain_station.py
module: scripts.substrate_drain_station
lines: 104
size: 3673
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_drain_station.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Operator entrypoint: drain one or more station inboxes once.

Runs the unified drain (events + results) and optionally reconciles recent
rituals so body_actions get their outcomes mirrored in-place.

...

**Lines:** 104 | **Size:** 3,673 bytes

## Depends On

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-ritual_reconciler-py]]
- [[eos_ai-substrate-station_drainer-py]]

## Contains

- **fn** [[scripts-substrate_drain_station-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate.result_query import latest_failed
from eos_ai.substrate.result_query import node_health_summary
from eos_ai.substrate.result_query import recent_open_close_summaries
from eos_ai.substrate.result_query import ritual_outcomes_summary
from eos_ai.substrate.result_query import station_readiness_report
from eos_ai.substrate.result_query import stats as result_stats
from eos_ai.substrate.result_query import unresolved_rituals
from eos_ai.substrate.local_listener import listener_report
from eos_ai.substrate.ritual_reconciler import reconcile_recent
from eos_ai.substrate.station_drainer import drain_all
```
