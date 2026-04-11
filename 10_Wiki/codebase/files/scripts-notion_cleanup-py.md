---
type: codebase-file
path: scripts/notion_cleanup.py
module: scripts.notion_cleanup
lines: 569
size: 19331
tags: [entry-point]
generated: 2026-04-11
---

# scripts/notion_cleanup.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Notion Cleanup — archives old scaffold databases
and creates individual role dashboard pages.

Problems to fix:
1. Archive old emoji-prefixed scaffold DBs:
...

**Lines:** 569 | **Size:** 19,331 bytes

## Contains

- **fn** [[scripts-notion_cleanup-py-_get_page_title]]`(page) → str`
- **fn** [[scripts-notion_cleanup-py-get_all_dbs]]`() → dict[str, dict]`
- **fn** [[scripts-notion_cleanup-py-get_child_page_titles]]`(page_id) → set[str]`
- **fn** [[scripts-notion_cleanup-py-archive_db]]`(db_id, label) → None`
- **fn** [[scripts-notion_cleanup-py-ensure_dashboards_page]]`(venture_page_id) → str`
- **fn** [[scripts-notion_cleanup-py-create_role_page]]`(parent_id, role) → str`
- **fn** [[scripts-notion_cleanup-py-create_stub_page]]`(venture_page_id, name, emoji, unlocks_at, description) → str`
- **fn** [[scripts-notion_cleanup-py-run_cleanup]]`() → None`

## Import Statements

```python
import os
import sys
import requests
from dotenv import load_dotenv
```
