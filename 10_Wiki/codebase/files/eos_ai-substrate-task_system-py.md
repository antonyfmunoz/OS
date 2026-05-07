---
type: codebase-file
path: eos_ai/substrate/task_system.py
module: eos_ai.substrate.task_system
lines: 602
size: 23121
generated: 2026-05-07
---

# eos_ai/substrate/task_system.py

Task autonomy and overnight execution system (v1).

Classifies tasks into execution policies (autonomous / needs_operator /
needs_approval), tracks their lifecycle, and dispatches based on the
current OperatorSession state.  Autonomous tasks execute immediately when
...

**Lines:** 602 | **Size:** 23,121 bytes

## Used By

- [[eos_ai-substrate-task_execution-py]]
- [[eos_ai-substrate-task_queue-py]]

## Contains

- **class** [[eos_ai-substrate-task_system-py-TaskExecutionPolicy]] — 0 methods
- **class** [[eos_ai-substrate-task_system-py-TaskStatus]] — 0 methods
- **class** [[eos_ai-substrate-task_system-py-Task]] — 3 methods
- **class** [[eos_ai-substrate-task_system-py-TaskStore]] — 12 methods
- **fn** [[eos_ai-substrate-task_system-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-task_system-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-task_system-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-task_system-py-classify_task]]`(text) → TaskExecutionPolicy`
- **fn** [[eos_ai-substrate-task_system-py-create_task]]`(text) → Task`
- **fn** [[eos_ai-substrate-task_system-py-process_task]]`(task) → Task`
- **fn** [[eos_ai-substrate-task_system-py-run_overnight_tasks]]`() → list[Task]`
- **fn** [[eos_ai-substrate-task_system-py-get_task_summary]]`() → dict`

## Import Statements

```python
from __future__ import annotations
import re
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional
```
