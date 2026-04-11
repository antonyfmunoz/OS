---
type: codebase-file
path: eos_ai/model_preferences.py
module: eos_ai.model_preferences
lines: 472
size: 19661
generated: 2026-04-11
---

# eos_ai/model_preferences.py

Multi-model router with business context awareness and full human override.

Priority order (highest to lowest):
  1. forced_model   — per-call human override
  2. session_override — human session override
...

**Lines:** 472 | **Size:** 19,661 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Used By

- [[eos_ai-agent_runtime-py]]

## Contains

- **class** [[eos_ai-model_preferences-py-ModelPreferences]] — 14 methods

## Import Statements

```python
import os
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
```
