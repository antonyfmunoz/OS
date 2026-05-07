---
type: codebase-file
path: scripts/demo_mvp_loop.py
module: scripts.demo_mvp_loop
lines: 284
size: 7403
tags: [entry-point]
generated: 2026-05-07
---

# scripts/demo_mvp_loop.py

> **ENTRY POINT** — Contains `if __name__` or server start.

UMH MVP Demo — exercises the complete operator loop.

Runs through: plan -> validate -> quality -> execute -> monitor -> summary
Uses internal APIs for reliability (no HTTP server needed).

...

**Lines:** 284 | **Size:** 7,403 bytes

## Contains

- **fn** [[scripts-demo_mvp_loop-py-_report]]`(name, passed, detail) → None`
- **fn** [[scripts-demo_mvp_loop-py-demo_path1_plan_only]]`() → None`
- **fn** [[scripts-demo_mvp_loop-py-demo_path2_execute_safe]]`() → None`
- **fn** [[scripts-demo_mvp_loop-py-demo_path3_enqueue_task]]`() → None`
- **fn** [[scripts-demo_mvp_loop-py-demo_path4_plan_rejection]]`() → None`
- **fn** [[scripts-demo_mvp_loop-py-demo_path5_summary_and_timeline]]`() → None`
- **fn** [[scripts-demo_mvp_loop-py-main]]`() → int`

## Import Statements

```python
import sys
import os
from umh.orchestrator.summary import summarize_task
from umh.orchestrator.task import Task
from umh.orchestrator.task import TaskStatus
from umh.orchestrator.task import TaskStep
from umh.orchestrator.task import enqueue_task
from umh.orchestrator.task import execute_task
from umh.orchestrator.timeline import build_task_timeline
from umh.planning.models import PlanObjective
from umh.planning.models import PlanStatus
from umh.planning.planner import create_plan
from umh.planning.planner import create_plan_from_raw
from umh.planning.planner import execute_plan
```
