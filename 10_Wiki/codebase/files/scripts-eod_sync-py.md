---
type: codebase-file
path: scripts/eod_sync.py
module: scripts.eod_sync
lines: 243
size: 8155
tags: [entry-point]
generated: 2026-04-12
---

# scripts/eod_sync.py

> **ENTRY POINT** — Contains `if __name__` or server start.

EOD Sync — 6pm PDT daily closing loop.
Sections: Meetings today | Purchases/expenses |
Project updates | Decisions made.
Posts to #morning-brief channel.

**Lines:** 243 | **Size:** 8,155 bytes

## Contains

- **fn** [[scripts-eod_sync-py-_get_todays_meetings]]`() → list[str]`
- **fn** [[scripts-eod_sync-py-_get_todays_purchases]]`() → list[str]`
- **fn** [[scripts-eod_sync-py-_get_todays_project_updates]]`(ctx) → list[str]`
- **fn** [[scripts-eod_sync-py-_get_todays_decisions]]`(ctx) → list[str]`
- **fn** [[scripts-eod_sync-py-build_eod_message]]`() → str`
- **fn** [[scripts-eod_sync-py-build_and_post_eod]]`()`

## Import Statements

```python
import os
import sys
import json
import asyncio
import discord
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
