---
type: codebase-file
path: eos_ai/substrate/task_queue.py
module: eos_ai.substrate.task_queue
lines: 245
size: 8714
generated: 2026-05-07
---

# eos_ai/substrate/task_queue.py

Priority queue layer for the task system.

Assigns priority scores and queue names to tasks, provides sorted retrieval
helpers. Tasks remain in the unified TaskStore — queue_name is a filter
dimension, not a separate data structure.
...

**Lines:** 245 | **Size:** 8,714 bytes

## Depends On

- [[eos_ai-substrate-task_system-py]]

## Contains

- **class** [[eos_ai-substrate-task_queue-py-TaskPriority]] — 0 methods
- **fn** [[eos_ai-substrate-task_queue-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-task_queue-py-infer_task_priority]]`(task, session) → int`
- **fn** [[eos_ai-substrate-task_queue-py-assign_queue]]`(task, is_day_open) → str`
- **fn** [[eos_ai-substrate-task_queue-py-prioritize_and_queue]]`(task, session, is_day_open) → Task`
- **fn** [[eos_ai-substrate-task_queue-py-_priority_sort]]`(tasks) → list[Task]`
- **fn** [[eos_ai-substrate-task_queue-py-get_ready_tasks]]`(store) → list[Task]`
- **fn** [[eos_ai-substrate-task_queue-py-get_overnight_tasks]]`(store) → list[Task]`
- **fn** [[eos_ai-substrate-task_queue-py-get_waiting_on_operator_tasks]]`(store) → list[Task]`
- **fn** [[eos_ai-substrate-task_queue-py-get_tasks_sorted_for_execution]]`(store) → list[Task]`
- **fn** [[eos_ai-substrate-task_queue-py-get_enhanced_task_summary]]`(store) → dict`
- **fn** [[eos_ai-substrate-task_queue-py-prepare_overnight_queue]]`(store) → dict`

## Import Statements

```python
from __future__ import annotations
import re
import sys
from enum import IntEnum
from typing import TYPE_CHECKING
from typing import Optional
from eos_ai.substrate.task_system import Task
from eos_ai.substrate.task_system import TaskExecutionPolicy
from eos_ai.substrate.task_system import TaskStatus
from eos_ai.substrate.task_system import TaskStore
```
