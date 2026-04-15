---
type: codebase-file
path: scripts/session_bootstrap.py
module: scripts.session_bootstrap
lines: 161
size: 5039
tags: [entry-point]
generated: 2026-04-12
---

# scripts/session_bootstrap.py

> **ENTRY POINT** — Contains `if __name__` or server start.

session_bootstrap.py — Mandatory context load at session start.

Prints, in order:
    1. cloud.md (root system context)
    2. 10_Wiki/palace/index.md (palace index)
...

**Lines:** 161 | **Size:** 5,039 bytes

## Depends On

- [[scripts-query_graph-py]]

## Contains

- **fn** [[scripts-session_bootstrap-py-_read]]`(path) → str`
- **fn** [[scripts-session_bootstrap-py-print_full]]`() → None`
- **fn** [[scripts-session_bootstrap-py-print_compact]]`() → None`
- **fn** [[scripts-session_bootstrap-py-check_freshness]]`() → int`
- **fn** [[scripts-session_bootstrap-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from scripts.query_graph import GraphQuery
```
