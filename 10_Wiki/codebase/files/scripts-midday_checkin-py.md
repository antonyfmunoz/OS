---
type: codebase-file
path: scripts/midday_checkin.py
module: scripts.midday_checkin
lines: 105
size: 3342
tags: [entry-point]
generated: 2026-05-07
---

# scripts/midday_checkin.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Mid-day check-in — runs at 12:30pm PDT.
Surfaces afternoon agenda, urgent pending items,
and one afternoon priority.

**Lines:** 105 | **Size:** 3,342 bytes

## Contains

- **fn** [[scripts-midday_checkin-py-midday_checkin]]`()`

## Import Statements

```python
import os
import sys
import asyncio
import discord
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
