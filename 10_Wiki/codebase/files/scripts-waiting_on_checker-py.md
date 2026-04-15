---
type: codebase-file
path: scripts/waiting_on_checker.py
module: scripts.waiting_on_checker
lines: 94
size: 2632
tags: [entry-point]
generated: 2026-04-12
---

# scripts/waiting_on_checker.py

> **ENTRY POINT** — Contains `if __name__` or server start.

WAITING_ON checker — scans emails in WAITING_ON folder
that are older than 48h and surfaces them in Discord.
Runs every morning at 6:05am after the brief.

**Lines:** 94 | **Size:** 2,632 bytes

## Contains

- **fn** [[scripts-waiting_on_checker-py-check_waiting_on]]`()`

## Import Statements

```python
import asyncio
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import discord
```
