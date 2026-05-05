---
type: codebase-file
path: scripts/notion_sync_poller.py
module: scripts.notion_sync_poller
lines: 44
size: 1153
tags: [entry-point]
generated: 2026-04-12
---

# scripts/notion_sync_poller.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Notion Sync Poller — runs every 15 minutes via cron.

1. Pushes Neon tasks without a notion_page_id → Notion
2. Pulls Notion status changes back → Neon events table
   (delegates to notion_tasks_sync.sync_neon_to_notion)

**Lines:** 44 | **Size:** 1,153 bytes

## Contains

- **fn** [[scripts-notion_sync_poller-py-run]]`()`

## Import Statements

```python
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
