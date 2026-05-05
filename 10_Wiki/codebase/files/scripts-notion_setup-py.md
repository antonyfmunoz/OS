---
type: codebase-file
path: scripts/notion_setup.py
module: scripts.notion_setup
lines: 1081
size: 37473
tags: [entry-point]
generated: 2026-04-12
---

# scripts/notion_setup.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Notion Setup — creates the full per-venture primitive database
architecture for EntrepreneurOS.

UNIVERSAL (all roles, all stages):
  Goals/OKRs, Tasks, Meetings, Documents,
...

**Lines:** 1081 | **Size:** 37,473 bytes

## Contains

- **fn** [[scripts-notion_setup-py-_to_env_key]]`(name) → str`
- **fn** [[scripts-notion_setup-py-_create_db]]`(parent_page_id, title, properties) → str`
- **fn** [[scripts-notion_setup-py-_get_all_dbs]]`() → dict`
- **fn** [[scripts-notion_setup-py-_ensure_db]]`(parent_id, title, schema, existing) → str`
- **fn** [[scripts-notion_setup-py-_get_existing_page_titles]]`(parent_id) → set`
- **fn** [[scripts-notion_setup-py-_ensure_dashboards_page]]`(venture_page_id) → str`
- **fn** [[scripts-notion_setup-py-_create_role_dashboard_page]]`(parent_id, role_name, dept, description, db_instructions) → str`
- **fn** [[scripts-notion_setup-py-main]]`() → None`

## Import Statements

```python
import os
import sys
import json
import requests
from dotenv import load_dotenv
from dotenv import set_key
```
