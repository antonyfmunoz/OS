---
type: codebase-file
path: scripts/bis_context.py
module: scripts.bis_context
lines: 88
size: 2509
tags: [entry-point]
generated: 2026-05-07
---

# scripts/bis_context.py

> **ENTRY POINT** — Contains `if __name__` or server start.

BIS context injector — prints active venture context from VENTURES_JSON.
Used by !`command` blocks in skills to inject live venture data.

Usage:
  python3 /opt/OS/scripts/bis_context.py              # default fields
...

**Lines:** 88 | **Size:** 2,509 bytes

## Contains

- **fn** [[scripts-bis_context-py-get_ventures]]`() → list[dict]`
- **fn** [[scripts-bis_context-py-get_active_venture]]`() → dict`
- **fn** [[scripts-bis_context-py-main]]`() → None`

## Import Statements

```python
import argparse
import json
import os
import sys
from dotenv import load_dotenv
```
