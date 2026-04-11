---
type: codebase-file
path: scripts/summarize_nodes.py
module: scripts.summarize_nodes
lines: 150
size: 4654
tags: [entry-point]
generated: 2026-04-11
---

# scripts/summarize_nodes.py

> **ENTRY POINT** — Contains `if __name__` or server start.

summarize_nodes.py — Append-only one-line summaries for every graph node.

Safe compression layer: we NEVER overwrite raw docstrings or source files.
Every run appends a new version record keyed by node id. Previous versions
stay in the file under "history" so nothing is lost.
...

**Lines:** 150 | **Size:** 4,654 bytes

## Contains

- **fn** [[scripts-summarize_nodes-py-_one_line]]`(docstring, fallback) → str`
- **fn** [[scripts-summarize_nodes-py-build_summaries]]`() → dict[str, Any]`
- **fn** [[scripts-summarize_nodes-py-_upsert]]`(store, nid, summary, ts, raw_doc) → int`
- **fn** [[scripts-summarize_nodes-py-show]]`(nid) → int`
- **fn** [[scripts-summarize_nodes-py-stats]]`() → int`
- **fn** [[scripts-summarize_nodes-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
```
