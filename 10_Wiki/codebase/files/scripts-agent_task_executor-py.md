---
type: codebase-file
path: scripts/agent_task_executor.py
module: scripts.agent_task_executor
lines: 346
size: 11638
tags: [entry-point]
generated: 2026-04-11
---

# scripts/agent_task_executor.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Agent Task Executor — polls the tasks table for
pending AI agent tasks, executes each through the
cognitive loop with the correct agent soul doc,
marks complete, and surfaces results to Discord.

...

**Lines:** 346 | **Size:** 11,638 bytes

## Contains

- **fn** [[scripts-agent_task_executor-py-load_soul_doc]]`(path) → str`
- **fn** [[scripts-agent_task_executor-py-execute_agent_task]]`(task, ctx) → dict`
- **fn** [[scripts-agent_task_executor-py-requires_approval]]`(task, result) → bool`
- **fn** [[scripts-agent_task_executor-py-run_executor]]`()`

## Import Statements

```python
import os
import sys
import asyncio
import discord
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
