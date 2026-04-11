---
type: codebase-file
path: scripts/merge_graphs.py
module: scripts.merge_graphs
lines: 214
size: 7348
tags: [entry-point]
generated: 2026-04-11
---

# scripts/merge_graphs.py

> **ENTRY POINT** — Contains `if __name__` or server start.

merge_graphs.py — Merge graphify_overlay.json into codebase_graph.json.

RULES (non-negotiable):
  - Primary graph (data/codebase_graph.json) is SOURCE OF TRUTH.
  - The overlay is ADDITIVE ONLY. Core edges are never replaced.
...

**Lines:** 214 | **Size:** 7,348 bytes

## Contains

- **fn** [[scripts-merge_graphs-py-_load_json]]`(path, label) → dict[str, Any]`
- **fn** [[scripts-merge_graphs-py-_edge_key]]`(e) → tuple[str, str, str, str, str]`
- **fn** [[scripts-merge_graphs-py-_overlay_edge_to_primary]]`(overlay_edge) → dict[str, Any]`
- **fn** [[scripts-merge_graphs-py-merge]]`() → dict[str, Any]`
- **fn** [[scripts-merge_graphs-py-_print_stats]]`() → int`
- **fn** [[scripts-merge_graphs-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any
```
