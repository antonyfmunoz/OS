---
type: codebase-file
path: scripts/day_reminder.py
module: scripts.day_reminder
lines: 117
size: 3566
tags: [entry-point]
generated: 2026-05-07
---

# scripts/day_reminder.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Day Reminder — fires reminders throughout the day.
Runs every 5 minutes via cron.
Checks for events starting in the next 10-15 minutes
and fires a Discord alert if not already sent.

**Lines:** 117 | **Size:** 3,566 bytes

## Contains

- **fn** [[scripts-day_reminder-py-check_and_remind]]`()`

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
