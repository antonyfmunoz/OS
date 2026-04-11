---
type: codebase-file
path: eos_ai/substrate/scene_capabilities.py
module: eos_ai.substrate.scene_capabilities
lines: 173
size: 6485
generated: 2026-04-11
---

# eos_ai/substrate/scene_capabilities.py

Scene → capability requirements — tiny explicit mapping.

Scenes in `scenes.SCENE_REGISTRY` are ordered recipes of SafeActions. Each
action implicitly needs a node capability to execute meaningfully:

...

**Lines:** 173 | **Size:** 6,485 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-capabilities-py]]
- [[eos_ai-substrate-scenes-py]]

## Used By

- [[eos_ai-substrate-scene_policy-py]]

## Contains

- **fn** [[eos_ai-substrate-scene_capabilities-py-_walk_scene]]`(scene, _seen) → list[frozenset[str]]`
- **fn** [[eos_ai-substrate-scene_capabilities-py-requirements_for]]`(scene_name) → set[str]`
- **fn** [[eos_ai-substrate-scene_capabilities-py-node_supports]]`(node, scene_name) → tuple[bool, set[str]]`
- **fn** [[eos_ai-substrate-scene_capabilities-py-scene_requirements_inventory]]`() → dict[str, list[str]]`

## Import Statements

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from typing import Iterable
from typing import Optional
from eos_ai.substrate.actions import ActionKind
from eos_ai.substrate.capabilities import Capability
from eos_ai.substrate.scenes import SCENE_REGISTRY
from eos_ai.substrate.scenes import Scene
```
