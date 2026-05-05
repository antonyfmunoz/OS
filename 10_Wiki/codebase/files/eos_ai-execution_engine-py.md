---
type: codebase-file
path: eos_ai/execution_engine.py
module: eos_ai.execution_engine
lines: 359
size: 13948
generated: 2026-04-12
---

# eos_ai/execution_engine.py

ExecutionEngine — formal lifecycle tracking for every task in the system.

Gives every task a visible, auditable lifecycle:
  queued → assigned → in_progress → blocked → completed → outcome_logged

...

**Lines:** 359 | **Size:** 13,948 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Contains

- **class** [[eos_ai-execution_engine-py-ExecutionEngine]] — 7 methods
- **fn** [[eos_ai-execution_engine-py-_notify]]`(text) → None`

## Import Statements

```python
from __future__ import annotations
import os
import datetime
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
```
