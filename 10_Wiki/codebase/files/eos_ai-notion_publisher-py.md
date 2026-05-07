---
type: codebase-file
path: eos_ai/notion_publisher.py
module: eos_ai.notion_publisher
lines: 496
size: 17142
generated: 2026-05-07
---

# eos_ai/notion_publisher.py

EOS Notion Publisher — canonical pattern for writing EOS content to Notion.

Every brief, report, summary, and diagnosis uses this module.
Never build a custom Notion writer from scratch.

...

**Lines:** 496 | **Size:** 17,142 bytes

## Contains

- **class** [[eos_ai-notion_publisher-py-NotionPublisher]] — 6 methods
- **fn** [[eos_ai-notion_publisher-py-_get_db_id]]`(venture_id, db_type) → str`
- **fn** [[eos_ai-notion_publisher-py-_api_call]]`(method, endpoint, payload) → dict`
- **fn** [[eos_ai-notion_publisher-py-_page_url]]`(page_id) → str`
- **fn** [[eos_ai-notion_publisher-py-_heading]]`(text, level) → dict`
- **fn** [[eos_ai-notion_publisher-py-_paragraph]]`(text) → dict`
- **fn** [[eos_ai-notion_publisher-py-_divider]]`() → dict`
- **fn** [[eos_ai-notion_publisher-py-_bulleted]]`(text) → dict`
- **fn** [[eos_ai-notion_publisher-py-_create_page]]`(parent_db_id, title, blocks, extra_properties) → str`
- **fn** [[eos_ai-notion_publisher-py-_find_page_by_title]]`(db_id, title) → str`
- **fn** [[eos_ai-notion_publisher-py-_brief_blocks]]`(content, title) → list`
- **fn** [[eos_ai-notion_publisher-py-get_publisher]]`(ctx) → NotionPublisher`

## Import Statements

```python
import json
import logging
import os
from datetime import date
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
