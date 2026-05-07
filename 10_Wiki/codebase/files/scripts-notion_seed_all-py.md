---
type: codebase-file
path: scripts/notion_seed_all.py
module: scripts.notion_seed_all
lines: 931
size: 35244
tags: [entry-point]
generated: 2026-05-07
---

# scripts/notion_seed_all.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Notion Seed All — seeds Empyrean Creative, Personal Brand ventures
and content calendars for all three ventures.

Lyfe Institute was already seeded in notion_seed.py.
This script completes the remaining two ventures.
...

**Lines:** 931 | **Size:** 35,244 bytes

## Depends On

- [[eos_ai-notion_sync-py]]

## Contains

- **fn** [[scripts-notion_seed_all-py-seed_empyrean]]`() → None`
- **fn** [[scripts-notion_seed_all-py-seed_personal_brand]]`() → None`
- **fn** [[scripts-notion_seed_all-py-seed_content_calendars]]`() → None`
- **fn** [[scripts-notion_seed_all-py-main]]`() → None`

## Import Statements

```python
import os
import sys
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
from eos_ai.notion_sync import write_document
from eos_ai.notion_sync import write_metric
```
