---
type: codebase-file
path: scripts/week_architect.py
module: scripts.week_architect
lines: 118
size: 3447
tags: [entry-point]
generated: 2026-04-12
---

# scripts/week_architect.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Week Architect — Sunday 8pm PDT.
Reviews the coming week, identifies gaps and conflicts,
suggests structure, posts to #general.
Runs after weekly review (7pm).

**Lines:** 118 | **Size:** 3,447 bytes

## Contains

- **fn** [[scripts-week_architect-py-architect_week]]`()`

## Import Statements

```python
import os
import sys
import asyncio
import discord
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
