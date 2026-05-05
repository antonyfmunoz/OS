---
type: codebase-file
path: scripts/substrate_control_layer_smoke_test.py
module: scripts.substrate_control_layer_smoke_test
lines: 130
size: 4867
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_control_layer_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Substrate Control Layer v1 — smoke test.

Validates the explicit, bounded execution bridge end-to-end without touching
hot-path or networking. Uses a temporary node_id namespace to keep the live
queue clean.

**Lines:** 130 | **Size:** 4,867 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_control_layer_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_control_layer_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import uuid
from eos_ai.substrate import control_bridge as cb
from eos_ai.substrate import control_commands as cc
from eos_ai.substrate import local_executor as lx
```
