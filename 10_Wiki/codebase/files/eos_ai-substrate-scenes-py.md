---
type: codebase-file
path: eos_ai/substrate/scenes.py
module: eos_ai.substrate.scenes
lines: 81
size: 2761
generated: 2026-04-12
---

# eos_ai/substrate/scenes.py

Scene registry — small, code-declared workstation bootstrap recipes.

A Scene is an ordered sequence of MVP-safe SafeAction steps that together
prepare a workstation for a particular mode of work. Scenes are NOT runtime-
definable in this pass: they are hardcoded here so the trust boundary cannot
...

**Lines:** 81 | **Size:** 2,761 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Used By

- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-scene_capabilities-py]]
- [[eos_ai-substrate-scene_policy-py]]
- [[eos_ai-substrate-station_daemon-py]]

## Contains

- **class** [[eos_ai-substrate-scenes-py-SceneStep]] — 0 methods
- **class** [[eos_ai-substrate-scenes-py-Scene]] — 0 methods
- **fn** [[eos_ai-substrate-scenes-py-_scene]]`(name, description) → tuple[str, Scene]`
- **fn** [[eos_ai-substrate-scenes-py-get_scene]]`(name) → Scene | None`
- **fn** [[eos_ai-substrate-scenes-py-list_scenes]]`() → list[str]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.actions import ActionKind
```
