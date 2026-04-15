---
type: codebase-file
path: scripts/portfolio_brief.py
module: scripts.portfolio_brief
lines: 128
size: 3942
tags: [entry-point]
generated: 2026-04-12
---

# scripts/portfolio_brief.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Sunday Portfolio Brief — runs at 6am every Sunday.
Scans all ventures, identifies binding constraint,
posts to Discord #general + creates Notion page.

**Lines:** 128 | **Size:** 3,942 bytes

## Contains

- **fn** [[scripts-portfolio_brief-py-post_to_notion]]`(brief, ventures) → str | None`
- **fn** [[scripts-portfolio_brief-py-run_portfolio_brief]]`()`

## Import Statements

```python
import os
import sys
import json
import asyncio
import discord
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
