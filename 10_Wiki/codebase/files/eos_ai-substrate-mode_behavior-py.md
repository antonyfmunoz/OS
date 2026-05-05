---
type: codebase-file
path: eos_ai/substrate/mode_behavior.py
module: eos_ai.substrate.mode_behavior
lines: 257
size: 8913
generated: 2026-04-12
---

# eos_ai/substrate/mode_behavior.py

Mode behavior shaping — post-router output shaping by substrate mode.

Purpose
-------
Applies lightweight, deterministic transformations to router output based
...

**Lines:** 257 | **Size:** 8,913 bytes

## Used By

- [[scripts-substrate_mode_behavior_control_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-mode_behavior-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-mode_behavior-py-_contains_internal_language]]`(text) → bool`
- **fn** [[eos_ai-substrate-mode_behavior-py-_strip_internal_lines]]`(text) → str`
- **fn** [[eos_ai-substrate-mode_behavior-py-_mask_internal_refs]]`(text) → str`
- **fn** [[eos_ai-substrate-mode_behavior-py-_enforce_builder_structure]]`(text) → str`
- **fn** [[eos_ai-substrate-mode_behavior-py-_shape_product]]`(text) → str`
- **fn** [[eos_ai-substrate-mode_behavior-py-shape_reply]]`(text) → str`
- **fn** [[eos_ai-substrate-mode_behavior-py-detect_internal_leakage]]`(text) → list[str]`

## Import Statements

```python
from __future__ import annotations
import re
import sys
from typing import Optional
```
