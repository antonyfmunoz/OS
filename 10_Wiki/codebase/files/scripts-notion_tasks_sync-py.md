---
type: codebase-file
path: scripts/notion_tasks_sync.py
module: scripts.notion_tasks_sync
lines: 282
size: 9406
tags: [entry-point]
generated: 2026-05-07
---

# scripts/notion_tasks_sync.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Notion Tasks → Neon Sync
Polls the three venture Tasks databases for new/updated items
and writes them to the Neon events table so they appear in the
morning brief Section 1 (Your list).

...

**Lines:** 282 | **Size:** 9,406 bytes

## Contains

- **fn** [[scripts-notion_tasks_sync-py-load_state]]`() → dict`
- **fn** [[scripts-notion_tasks_sync-py-save_state]]`(state)`
- **fn** [[scripts-notion_tasks_sync-py-query_database]]`(db_id) → list`
- **fn** [[scripts-notion_tasks_sync-py-extract_task]]`(page) → dict`
- **fn** [[scripts-notion_tasks_sync-py-write_to_neon]]`(task, venture_id) → bool`
- **fn** [[scripts-notion_tasks_sync-py-push_status_to_notion]]`(notion_page_id, status, assigned_to) → bool`
- **fn** [[scripts-notion_tasks_sync-py-sync_neon_to_notion]]`() → int`
- **fn** [[scripts-notion_tasks_sync-py-run_sync]]`()`

## Import Statements

```python
import sys
import os
import json
import requests
from datetime import datetime
from datetime import timezone
from pathlib import Path
from dotenv import load_dotenv
```
