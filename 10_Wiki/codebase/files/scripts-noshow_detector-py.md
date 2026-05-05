---
type: codebase-file
path: scripts/noshow_detector.py
module: scripts.noshow_detector
lines: 156
size: 5194
tags: [entry-point]
generated: 2026-04-12
---

# scripts/noshow_detector.py

> **ENTRY POINT** — Contains `if __name__` or server start.

No-show detector — checks meetings that started 30+ min ago with no
outcome captured, marks as no-show, triggers recovery flow.
Runs every 15 minutes via cron.

**Lines:** 156 | **Size:** 5,194 bytes

## Contains

- **fn** [[scripts-noshow_detector-py-detect_noshows]]`()`

## Import Statements

```python
import os
import sys
import json
import asyncio
import discord
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
