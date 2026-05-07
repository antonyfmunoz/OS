---
type: codebase-file
path: scripts/build_notion_databases.py
module: scripts.build_notion_databases
lines: 117
size: 4383
generated: 2026-05-07
---

# scripts/build_notion_databases.py

Create the 9 databases that failed in the first build pass.

**Lines:** 117 | **Size:** 4,383 bytes

## Contains

- **fn** [[scripts-build_notion_databases-py-create_database]]`(parent_id, title, icon, properties)`

## Import Statements

```python
import sys
from dotenv import load_dotenv
from notion_client import Client
import os
```
