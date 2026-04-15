---
type: codebase-file
path: scripts/weekly_review.py
module: scripts.weekly_review
lines: 241
size: 8486
tags: [entry-point]
generated: 2026-04-12
---

# scripts/weekly_review.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Weekly business review — Sunday 7pm PDT.
Portfolio health, open items, DEX synthesis.
Posts to #general.

**Lines:** 241 | **Size:** 8,486 bytes

## Contains

- **fn** [[scripts-weekly_review-py-run_weekly_review]]`()`

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
