---
type: codebase-file
path: scripts/incremental_graph.py
module: scripts.incremental_graph
lines: 773
size: 28826
tags: [entry-point]
generated: 2026-04-12
---

# scripts/incremental_graph.py

> **ENTRY POINT** — Contains `if __name__` or server start.

incremental_graph.py — Dirty-set incremental updates for the codebase graph.

Rebuilds ONLY the parts of data/codebase_graph.json affected by a small set
of changed files. Falls back to a full rebuild (via scripts/codebase_graph.py)
when the change set is too large or the dirty region becomes inconsistent.
...

**Lines:** 773 | **Size:** 28,826 bytes

## Depends On

- [[scripts-codebase_graph-py]]

## Used By

- [[scripts-watch_graph-py]]

## Contains

- **fn** [[scripts-incremental_graph-py-_load_graph]]`() → dict[str, Any]`
- **fn** [[scripts-incremental_graph-py-_save_graph]]`(data) → None`
- **fn** [[scripts-incremental_graph-py-_rel]]`(path) → str`
- **fn** [[scripts-incremental_graph-py-_is_tracked]]`(rel) → bool`
- **fn** [[scripts-incremental_graph-py-_classify]]`(rel) → str`
- **fn** [[scripts-incremental_graph-py-_file_imported_by]]`(graph) → dict[str, set[str]]`
- **fn** [[scripts-incremental_graph-py-_compute_dirty_set]]`(graph, changed_rels) → tuple[set[str], set[str], set[str]]`
- **fn** [[scripts-incremental_graph-py-_node_ids_for_files]]`(graph, files) → set[str]`
- **fn** [[scripts-incremental_graph-py-_strip_dirty]]`(graph, dirty_files) → None`
- **fn** [[scripts-incremental_graph-py-_strip_non_python]]`(graph, dirty_np) → None`
- **fn** [[scripts-incremental_graph-py-_scan_python_files]]`(dirty) → tuple[dict[str, FileNode], dict[str, ClassNode], dict[str, FunctionNode]]`
- **fn** [[scripts-incremental_graph-py-_scan_non_python_file]]`(rel) → dict[str, Any] | None`
- **fn** [[scripts-incremental_graph-py-_edge_to_dict]]`(e) → dict[str, str]`
- **fn** [[scripts-incremental_graph-py-_recompute_edges_for_dirty]]`(graph, new_files, new_classes, new_functions) → list[dict[str, str]]`
- **fn** [[scripts-incremental_graph-py-_recompute_stats]]`(graph) → None`
- **fn** [[scripts-incremental_graph-py-_run_full_rebuild]]`(reason) → dict[str, Any]`
- **fn** [[scripts-incremental_graph-py-update]]`(changed_paths) → dict[str, Any]`
- **fn** [[scripts-incremental_graph-py-_print_stats]]`() → int`
- **fn** [[scripts-incremental_graph-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Iterable
from scripts.codebase_graph import CodebaseGraph
from scripts.codebase_graph import ClassNode
from scripts.codebase_graph import Edge
from scripts.codebase_graph import FileNode
from scripts.codebase_graph import FunctionNode
from scripts.codebase_graph import NON_PYTHON_EXTENSIONS
from scripts.codebase_graph import ROOT
from scripts.codebase_graph import SCAN_DIRS
from scripts.codebase_graph import SKIP_DIRS
from scripts.codebase_graph import SKIP_FILES
from scripts.codebase_graph import _module_name
from scripts.codebase_graph import scan_file
```
