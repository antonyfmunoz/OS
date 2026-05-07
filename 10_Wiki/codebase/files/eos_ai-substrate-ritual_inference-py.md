---
type: codebase-file
path: eos_ai/substrate/ritual_inference.py
module: eos_ai.substrate.ritual_inference
lines: 199
size: 7280
generated: 2026-05-07
---

# eos_ai/substrate/ritual_inference.py

Ritual hint inference — infer a scene hint when the operator did not
supply one, using only deterministic signals already present in the
ritual history and node registry.

Why this exists
...

**Lines:** 199 | **Size:** 7,280 bytes

## Depends On

- [[eos_ai-substrate-nodes-py]]

## Used By

- [[eos_ai-substrate-ritual_body-py]]

## Contains

- **class** [[eos_ai-substrate-ritual_inference-py-InferredHint]] — 1 methods
- **fn** [[eos_ai-substrate-ritual_inference-py-_last_successful_scene_for_node]]`(node_id) → Optional[str]`
- **fn** [[eos_ai-substrate-ritual_inference-py-_role_preferred_scene]]`(node) → Optional[str]`
- **fn** [[eos_ai-substrate-ritual_inference-py-infer_open_scene_hint]]`(node_id) → InferredHint`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from typing import Optional
from eos_ai.substrate.nodes import Node
from eos_ai.substrate.nodes import NodeRegistry
```
