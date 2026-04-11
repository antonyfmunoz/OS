---
type: codebase-file
path: eos_ai/substrate/station_readiness.py
module: eos_ai.substrate.station_readiness
lines: 306
size: 11439
generated: 2026-04-11
---

# eos_ai/substrate/station_readiness.py

Station readiness — derived view of whether a node is fit for ritual work.

Pure derivation. No new state. No persistence. Reads:
  - NodeRegistry  (last_seen, declared status)
  - ResultStore   (recent outcomes, fallbacks, kinds)
...

**Lines:** 306 | **Size:** 11,439 bytes

## Depends On

- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-result_store-py]]

## Used By

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-scene_policy-py]]

## Contains

- **class** [[eos_ai-substrate-station_readiness-py-StationReadiness]] — 1 methods
- **fn** [[eos_ai-substrate-station_readiness-py-_utcnow]]`() → datetime`
- **fn** [[eos_ai-substrate-station_readiness-py-_parse_iso]]`(value) → Optional[datetime]`
- **fn** [[eos_ai-substrate-station_readiness-py-_age_seconds]]`(value) → Optional[float]`
- **fn** [[eos_ai-substrate-station_readiness-py-_count_unresolved_for_node]]`(node_id, store) → int`
- **fn** [[eos_ai-substrate-station_readiness-py-station_readiness]]`(node_id) → StationReadiness`
- **fn** [[eos_ai-substrate-station_readiness-py-is_ready]]`(node_id) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.result_query import node_health_summary
from eos_ai.substrate.result_store import ResultStore
from eos_ai.substrate.result_store import get_result_store
```
