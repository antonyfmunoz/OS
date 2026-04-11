---
type: codebase-file
path: eos_ai/substrate/scene_policy.py
module: eos_ai.substrate.scene_policy
lines: 244
size: 7905
generated: 2026-04-11
---

# eos_ai/substrate/scene_policy.py

Scene policy — deterministic mapping from (node, readiness, hint) → scene.

NOT a rules engine. NOT runtime-configurable. A small pure function with a
fixed table so the substrate stays inspectable: any operator can read this
file and know exactly which scene a ritual will pick.
...

**Lines:** 244 | **Size:** 7,905 bytes

## Depends On

- [[eos_ai-substrate-scene_capabilities-py]]
- [[eos_ai-substrate-scenes-py]]
- [[eos_ai-substrate-station_readiness-py]]

## Used By

- [[eos_ai-substrate-ritual_body-py]]

## Contains

- **class** [[eos_ai-substrate-scene_policy-py-SceneDecision]] — 1 methods
- **fn** [[eos_ai-substrate-scene_policy-py-_lookup_node]]`(node_id)`
- **fn** [[eos_ai-substrate-scene_policy-py-_capability_guarded]]`(node_id, scene, base_reason, classification) → 'SceneDecision'`
- **fn** [[eos_ai-substrate-scene_policy-py-_resolve_classification]]`(readiness) → str`
- **fn** [[eos_ai-substrate-scene_policy-py-_normalize_hint]]`(requested_mode) → Optional[str]`
- **fn** [[eos_ai-substrate-scene_policy-py-select_scene]]`(node_id, readiness, requested_mode) → SceneDecision`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from typing import Optional
from typing import Union
from eos_ai.substrate.scene_capabilities import node_supports
from eos_ai.substrate.scene_capabilities import requirements_for
from eos_ai.substrate.scenes import get_scene
from eos_ai.substrate.station_readiness import DEGRADED
from eos_ai.substrate.station_readiness import READY
from eos_ai.substrate.station_readiness import UNAVAILABLE
from eos_ai.substrate.station_readiness import StationReadiness
```
