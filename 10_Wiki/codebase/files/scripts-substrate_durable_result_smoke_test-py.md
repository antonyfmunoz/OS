---
type: codebase-file
path: scripts/substrate_durable_result_smoke_test.py
module: scripts.substrate_durable_result_smoke_test
lines: 235
size: 8648
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_durable_result_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Substrate durable-result smoke test.

Proves the ResultStore + ritual reconciliation loop survives a process
boundary. We can't fork a real subprocess cheaply here, so we simulate
the boundary by:
...

**Lines:** 235 | **Size:** 8,648 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-result_store-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-ritual_reconciler-py]]
- [[eos_ai-substrate-ritual_runner-py]]
- [[eos_ai-substrate-rituals-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_drainer-py]]

## Contains

- **fn** [[scripts-substrate_durable_result_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_durable_result_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.result_query import by_action_id
from eos_ai.substrate.result_query import latest
from eos_ai.substrate.result_query import latest_by_kind
from eos_ai.substrate.result_query import latest_by_node
from eos_ai.substrate.result_query import latest_failed
from eos_ai.substrate.result_query import node_health_summary
from eos_ai.substrate.result_query import ritual_outcomes_summary
from eos_ai.substrate.result_query import stats as result_stats
from eos_ai.substrate.result_query import unresolved_rituals
from eos_ai.substrate.actions import ActionResult
from eos_ai.substrate.actions import ActionStatus
from eos_ai.substrate.result_store import get_result_store
from eos_ai.substrate.result_store import reset_result_store_for_tests
from eos_ai.substrate.ritual_body import RitualPolicy
from eos_ai.substrate.ritual_reconciler import reconcile_ritual
from eos_ai.substrate.ritual_runner import start_open_day
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.station_drainer import drain_all
```
