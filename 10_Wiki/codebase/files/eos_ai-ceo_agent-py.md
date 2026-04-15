---
type: codebase-file
path: eos_ai/ceo_agent.py
module: eos_ai.ceo_agent
lines: 375
size: 14833
generated: 2026-04-12
---

# eos_ai/ceo_agent.py

CEOAgent — one per company, strategy layer.

Reads primitives from context automatically (never asks the founder).
Reasons about org chart composition based on stage and reality.
Monitors for stage transitions and evolves the org chart.
...

**Lines:** 375 | **Size:** 14,833 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-ceo_agent-py-CEOAgent]] — 8 methods

## Import Statements

```python
import json
import os
from typing import Optional
from eos_ai.context import EOSContext
```
