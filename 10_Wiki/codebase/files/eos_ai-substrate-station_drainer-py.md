---
type: codebase-file
path: eos_ai/substrate/station_drainer.py
module: eos_ai.substrate.station_drainer
lines: 348
size: 11411
generated: 2026-05-07
---

# eos_ai/substrate/station_drainer.py

Station drainer — EOS-side ingestion seam for inbox messages.

Completes two round-trip loops:

    1) EVENTS
...

**Lines:** 348 | **Size:** 11,411 bytes

## Depends On

- [[eos_ai-substrate-result_store-py]]
- [[eos_ai-substrate-station-py]]
- [[eos_ai-substrate-station_bus-py]]

## Used By

- [[scripts-substrate_drain_station-py]]
- [[scripts-substrate_drainer_smoke_test-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]
- [[scripts-substrate_voice_session_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-station_drainer-py-DrainStats]] — 1 methods
- **class** [[eos_ai-substrate-station_drainer-py-ResultDrainStats]] — 1 methods
- **class** [[eos_ai-substrate-station_drainer-py-DrainAllStats]] — 1 methods
- **fn** [[eos_ai-substrate-station_drainer-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-station_drainer-py-_hydrate_event]]`(payload, expected_node) → Optional[StationEvent]`
- **fn** [[eos_ai-substrate-station_drainer-py-_hydrate_result]]`(payload, node_id) → Optional[IngestedResult]`
- **fn** [[eos_ai-substrate-station_drainer-py-drain_node]]`(node_id) → DrainStats`
- **fn** [[eos_ai-substrate-station_drainer-py-drain_results]]`(node_id) → ResultDrainStats`
- **fn** [[eos_ai-substrate-station_drainer-py-drain_all]]`(node_id) → DrainAllStats`
- **fn** [[eos_ai-substrate-station_drainer-py-drain_nodes]]`(node_ids) → list[DrainAllStats]`
- **fn** [[eos_ai-substrate-station_drainer-py-_ingest_events]]`(node_id, event_msgs) → DrainStats`
- **fn** [[eos_ai-substrate-station_drainer-py-_ingest_results]]`(node_id, result_msgs) → ResultDrainStats`

## Import Statements

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from typing import Optional
from eos_ai.substrate.result_store import IngestedResult
from eos_ai.substrate.result_store import ResultStore
from eos_ai.substrate.result_store import get_result_store
from eos_ai.substrate.station import StationContract
from eos_ai.substrate.station import StationEvent
from eos_ai.substrate.station_bus import StationBus
from eos_ai.substrate.station_bus import get_station_bus
```
