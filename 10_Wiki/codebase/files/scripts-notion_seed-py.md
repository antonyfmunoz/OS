---
type: codebase-file
path: scripts/notion_seed.py
module: scripts.notion_seed
lines: 506
size: 17117
tags: [entry-point]
generated: 2026-05-07
---

# scripts/notion_seed.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Notion Seed — populates initial rows in EOS Notion databases.
Run once after notion_setup.py has created all DBs.
Idempotent in effect (creates rows, does not check for duplicates —
safe to re-run on empty DBs, do not re-run on populated ones).

**Lines:** 506 | **Size:** 17,117 bytes

## Depends On

- [[eos_ai-notion_sync-py]]

## Contains

- **fn** [[scripts-notion_seed-py-seed_portfolio]]`() → None`
- **fn** [[scripts-notion_seed-py-seed_roles]]`(venture_id, venture_name) → None`
- **fn** [[scripts-notion_seed-py-seed_tools]]`(venture_id, venture_name) → None`
- **fn** [[scripts-notion_seed-py-seed_goals]]`(venture_id, venture_name) → None`
- **fn** [[scripts-notion_seed-py-main]]`() → None`

## Import Statements

```python
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv
from eos_ai.notion_sync import get_db_id
from eos_ai.notion_sync import HEADERS
from eos_ai.notion_sync import _title
from eos_ai.notion_sync import _select
from eos_ai.notion_sync import _text
from eos_ai.notion_sync import _number
from eos_ai.notion_sync import _date
from eos_ai.notion_sync import _checkbox
from eos_ai.notion_sync import _create_page
```
