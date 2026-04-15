---
type: codebase-file
path: eos_ai/system_context.py
module: eos_ai.system_context
lines: 205
size: 7663
generated: 2026-04-12
---

# eos_ai/system_context.py

SystemContext — interface-aware intelligence layer.

Detects which interface is making AI calls and applies
the correct authority scope, validation rules, and prompt
context for that environment.
...

**Lines:** 205 | **Size:** 7,663 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-system_context-py-SystemContext]] — 3 methods

## Import Statements

```python
import os
import json
import sys
from pathlib import Path
from eos_ai.context import EOSContext
```
