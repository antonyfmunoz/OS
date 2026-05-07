---
type: codebase-file
path: eos_ai/model_preferences.py
module: eos_ai.model_preferences
lines: 472
size: 20132
generated: 2026-05-07
---

# eos_ai/model_preferences.py

Multi-model router with business context awareness and full human override.

Priority order (highest to lowest):
  1. forced_model   — per-call human override
  2. session_override — human session override
...

**Lines:** 472 | **Size:** 20,132 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Contains

- **class** [[eos_ai-model_preferences-py-ModelPreferences]] — 14 methods

## Import Statements

```python
import os
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
```
