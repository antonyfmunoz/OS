---
type: codebase-file
path: scripts/build_notion_workspace.py
module: scripts.build_notion_workspace
lines: 713
size: 26458
generated: 2026-04-12
---

# scripts/build_notion_workspace.py

Build EOS Notion Workspace
Mirrors the end game UI structure exactly.
Every section maps to a route in the SaaS UI.

**Lines:** 713 | **Size:** 26,458 bytes

## Contains

- **fn** [[scripts-build_notion_workspace-py-create_page]]`(parent_id, title, icon, content_blocks)`
- **fn** [[scripts-build_notion_workspace-py-create_database]]`(parent_id, title, icon, properties)`
- **fn** [[scripts-build_notion_workspace-py-text_block]]`(content)`
- **fn** [[scripts-build_notion_workspace-py-heading_block]]`(content, level)`
- **fn** [[scripts-build_notion_workspace-py-divider_block]]`()`
- **fn** [[scripts-build_notion_workspace-py-callout_block]]`(content, emoji)`

## Import Statements

```python
import sys
from dotenv import load_dotenv
from notion_client import Client
import os
```
