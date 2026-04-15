---
type: codebase-file
path: scripts/notion_outcome_sync.py
module: scripts.notion_outcome_sync
lines: 197
size: 5751
tags: [entry-point]
generated: 2026-04-12
---

# scripts/notion_outcome_sync.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Notion → Neon Outcome Sync
Polls the Notion Pipeline database for stage changes and fires
log_standalone_outcome() into Neon when a lead reaches a terminal stage.

Run on a schedule — every 15 minutes via cron or nightly_maintenance.sh.
...

**Lines:** 197 | **Size:** 5,751 bytes

## Contains

- **fn** [[scripts-notion_outcome_sync-py-load_state]]`() → dict`
- **fn** [[scripts-notion_outcome_sync-py-save_state]]`(state)`
- **fn** [[scripts-notion_outcome_sync-py-query_pipeline]]`() → list`
- **fn** [[scripts-notion_outcome_sync-py-extract_page_data]]`(page) → dict`
- **fn** [[scripts-notion_outcome_sync-py-fire_outcome]]`(page_data, outcome_type)`
- **fn** [[scripts-notion_outcome_sync-py-run_sync]]`()`

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
