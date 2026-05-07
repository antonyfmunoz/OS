---
type: codebase-file
path: eos_ai/context_builder.py
module: eos_ai.context_builder
lines: 520
size: 20333
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/context_builder.py

> **ENTRY POINT** — Contains `if __name__` or server start.

ContextBuilder — single-pass context assembly for the execution spine.

Replaces the 25 manual injection steps in cognitive_loop.py with one call:
    builder = ContextBuilder()
    ctx_result = builder.build(ctx, message, session_id, ...)
...

**Lines:** 520 | **Size:** 20,333 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-context_builder-py-UnifiedContext]] — 1 methods
- **class** [[eos_ai-context_builder-py-ContextBuilder]] — 1 methods

## Import Statements

```python
import json
import os
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from eos_ai.context import EOSContext
```
