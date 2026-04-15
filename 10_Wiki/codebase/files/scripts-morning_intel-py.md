---
type: codebase-file
path: scripts/morning_intel.py
module: scripts.morning_intel
lines: 179
size: 5642
tags: [entry-point]
generated: 2026-04-12
---

# scripts/morning_intel.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Morning Intelligence Brief — runs at 5:45am PDT daily,
before the morning brief. Synthesizes overnight signals,
market movements, and relevant news into a concise
intelligence brief posted to #general.

**Lines:** 179 | **Size:** 5,642 bytes

## Contains

- **fn** [[scripts-morning_intel-py-build_intel_brief]]`()`

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
