---
type: codebase-file
path: scripts/deadline_monitor.py
module: scripts.deadline_monitor
lines: 183
size: 6254
tags: [entry-point]
generated: 2026-05-07
---

# scripts/deadline_monitor.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Deadline Monitor — checks tasks with due dates
approaching or overdue. Runs every morning at 6:10am.
Alerts in Discord.

**Lines:** 183 | **Size:** 6,254 bytes

## Contains

- **fn** [[scripts-deadline_monitor-py-check_deadlines]]`()`
- **fn** [[scripts-deadline_monitor-py-check_stale_tasks]]`()`

## Import Statements

```python
import os
import sys
import asyncio
import discord
import json
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
