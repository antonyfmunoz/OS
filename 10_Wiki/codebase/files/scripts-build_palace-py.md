---
type: codebase-file
path: scripts/build_palace.py
module: scripts.build_palace
lines: 484
size: 16461
tags: [entry-point]
generated: 2026-04-12
---

# scripts/build_palace.py

> **ENTRY POINT** — Contains `if __name__` or server start.

build_palace.py — Generates the EOS memory palace from the graph.

Structure:
    Palace     -> 10_Wiki/palace/index.md
    Wing       -> 10_Wiki/palace/wings/<wing>.md          (top-level module)
...

**Lines:** 484 | **Size:** 16,461 bytes

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
- **fn** [[scripts-build_palace-py-_render_candidate_room]]`(cluster) → str`
- **fn** [[scripts-build_palace-py-_load_overlay_clusters]]`() → list[dict[str, Any]]`
- **fn** [[scripts-build_palace-py-build]]`(verbose, with_overlay) → dict[str, Any]`
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
