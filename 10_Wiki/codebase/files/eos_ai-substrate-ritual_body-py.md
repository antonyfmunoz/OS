---
type: codebase-file
path: eos_ai/substrate/ritual_body.py
module: eos_ai.substrate.ritual_body
lines: 342
size: 13596
generated: 2026-04-12
---

# eos_ai/substrate/ritual_body.py

Ritual body — tiny executable layer for open_day / close_day.

Rituals have historically been pure lifecycle markers (PENDING → … → COMPLETED)
with no side effects beyond state transitions. This module adds the smallest
useful executable layer: a declarative `RitualPolicy` that maps a ritual
...

**Lines:** 342 | **Size:** 13,596 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-ritual_inference-py]]
- [[eos_ai-substrate-rituals-py]]
- [[eos_ai-substrate-scene_policy-py]]
- [[eos_ai-substrate-scenes-py]]
- [[eos_ai-substrate-station_helpers-py]]
- [[eos_ai-substrate-station_readiness-py]]

## Used By

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-ritual_runner-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]
- [[scripts-substrate_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-ritual_body-py-RitualPolicy]] — 0 methods
- **fn** [[eos_ai-substrate-ritual_body-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-ritual_body-py-_resolve_station]]`(policy) → tuple[Optional[str], Optional[str]]`
- **fn** [[eos_ai-substrate-ritual_body-py-_record]]`(body_actions, kind, detail, action) → None`
- **fn** [[eos_ai-substrate-ritual_body-py-run_open_day_body]]`(ritual_id, policy) → list[dict]`
- **fn** [[eos_ai-substrate-ritual_body-py-run_close_day_body]]`(ritual_id, policy) → list[dict]`

## Import Statements

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from dataclasses import field
from typing import Optional
from eos_ai.substrate.actions import SafeAction
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.result_query import node_health_summary
from eos_ai.substrate.ritual_inference import InferredHint
from eos_ai.substrate.ritual_inference import infer_open_scene_hint
from eos_ai.substrate.rituals import Ritual
from eos_ai.substrate.rituals import RitualKind
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.scene_policy import select_scene
from eos_ai.substrate.scenes import get_scene
from eos_ai.substrate.station_helpers import propose_open_scene
from eos_ai.substrate.station_helpers import propose_play_sound
from eos_ai.substrate.station_helpers import propose_speak_text
from eos_ai.substrate.station_readiness import DEGRADED
from eos_ai.substrate.station_readiness import READY
from eos_ai.substrate.station_readiness import UNAVAILABLE
from eos_ai.substrate.station_readiness import StationReadiness
from eos_ai.substrate.station_readiness import station_readiness
```
