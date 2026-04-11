---
type: codebase-file
path: scripts/build_palace.py
module: scripts.build_palace
lines: 393
size: 13136
tags: [entry-point]
generated: 2026-04-11
---

# scripts/build_palace.py

> **ENTRY POINT** — Contains `if __name__` or server start.

build_palace.py — Generates the EOS memory palace from the graph.

Structure:
    Palace     -> 10_Wiki/palace/index.md
    Wing       -> 10_Wiki/palace/wings/<wing>.md          (top-level module)
...

**Lines:** 393 | **Size:** 13,136 bytes

## Depends On

- [[scripts-query_graph-py]]

## Contains

- **fn** [[scripts-build_palace-py-_wikilink_for_file]]`(path) → str`
- **fn** [[scripts-build_palace-py-score_file]]`(q, path) → int`
- **fn** [[scripts-build_palace-py-select_loci]]`(q, room) → list[dict[str, Any]]`
- **fn** [[scripts-build_palace-py-render_room]]`(room, loci) → str`
- **fn** [[scripts-build_palace-py-render_wing]]`(wing, rooms) → str`
- **fn** [[scripts-build_palace-py-render_index]]`(rooms_by_wing, stats) → str`
- **fn** [[scripts-build_palace-py-_graph_freshness]]`(q) → tuple[bool, float]`
- **fn** [[scripts-build_palace-py-build]]`(verbose) → dict[str, Any]`
- **fn** [[scripts-build_palace-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Any
from scripts.query_graph import GraphQuery
```
