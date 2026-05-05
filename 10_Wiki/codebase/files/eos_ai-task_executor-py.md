---
type: codebase-file
path: eos_ai/task_executor.py
module: eos_ai.task_executor
lines: 282
size: 10177
generated: 2026-04-12
---

# eos_ai/task_executor.py

TaskExecutor — agent task execution layer.

Agents don't just respond — they execute typed tasks.
Each task type has a handler. High-risk tasks require approval.
All task executions are persisted to Neon for audit.
...

**Lines:** 282 | **Size:** 10,177 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-task_executor-py-TaskStatus]] — 0 methods
- **class** [[eos_ai-task_executor-py-AgentTask]] — 0 methods
- **class** [[eos_ai-task_executor-py-TaskExecutor]] — 12 methods

## Import Statements

```python
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Optional
from eos_ai.context import EOSContext
```
