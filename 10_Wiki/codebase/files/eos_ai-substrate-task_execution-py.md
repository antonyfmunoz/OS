---
type: codebase-file
path: eos_ai/substrate/task_execution.py
module: eos_ai.substrate.task_execution
lines: 504
size: 19330
generated: 2026-05-07
---

# eos_ai/substrate/task_execution.py

Real task execution pipeline — binds tasks to tmux-backed Claude sessions.

Replaces the v1 stub (immediate completion) with actual dispatch through
the existing claude_session_bridge infrastructure. Tasks are routed via
capability_routing, sent to the correct tmux session, and their output
...

**Lines:** 504 | **Size:** 19,330 bytes

## Depends On

- [[eos_ai-substrate-task_system-py]]

## Contains

- **fn** [[eos_ai-substrate-task_execution-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-task_execution-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-task_execution-py-_resolve_tmux_target]]`(chosen_target) → tuple[str, str]`
- **fn** [[eos_ai-substrate-task_execution-py-detect_human_block]]`(text) → Optional[str]`
- **fn** [[eos_ai-substrate-task_execution-py-execute_task]]`(task, session) → Task`
- **fn** [[eos_ai-substrate-task_execution-py-_execute_via_pipeline]]`(task, session) → Task`
- **fn** [[eos_ai-substrate-task_execution-py-_sync_pipeline_to_task]]`(task, pipeline) → None`
- **fn** [[eos_ai-substrate-task_execution-py-_execute_legacy]]`(task, session) → Task`
- **fn** [[eos_ai-substrate-task_execution-py-_build_dispatch_text]]`(task) → str`
- **fn** [[eos_ai-substrate-task_execution-py-run_overnight_execution]]`(session) → dict`

## Import Statements

```python
from __future__ import annotations
import re
import sys
from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING
from typing import Optional
from eos_ai.substrate.task_system import Task
from eos_ai.substrate.task_system import TaskExecutionPolicy
from eos_ai.substrate.task_system import TaskStatus
from eos_ai.substrate.task_system import TaskStore
```
