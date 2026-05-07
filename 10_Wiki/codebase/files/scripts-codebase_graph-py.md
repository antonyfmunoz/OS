---
type: codebase-file
path: scripts/codebase_graph.py
module: scripts.codebase_graph
lines: 1214
size: 45016
tags: [entry-point]
generated: 2026-05-07
---

# scripts/codebase_graph.py

> **ENTRY POINT** — Contains `if __name__` or server start.

codebase_graph.py — Persistent codebase knowledge graph for EOS.

Scans the entire codebase using Python AST, extracts structure,
dependencies, and relationships, then generates an Obsidian vault
of interconnected markdown files with wikilinks.
...

**Lines:** 1214 | **Size:** 45,016 bytes

## Used By

- [[scripts-incremental_graph-py]]

## Contains

- **class** [[scripts-codebase_graph-py-FunctionNode]] — 0 methods
- **class** [[scripts-codebase_graph-py-ClassNode]] — 0 methods
- **class** [[scripts-codebase_graph-py-FileNode]] — 0 methods
- **class** [[scripts-codebase_graph-py-Edge]] — 0 methods
- **class** [[scripts-codebase_graph-py-CodebaseGraph]] — 0 methods
- **fn** [[scripts-codebase_graph-py-_rel]]`(path) → str`
- **fn** [[scripts-codebase_graph-py-_module_name]]`(path) → str`
- **fn** [[scripts-codebase_graph-py-_decorator_name]]`(node) → str`
- **fn** [[scripts-codebase_graph-py-_extract_calls]]`(node) → list[str]`
- **fn** [[scripts-codebase_graph-py-_annotation_str]]`(node) → str | None`
- **fn** [[scripts-codebase_graph-py-_is_entry_point]]`(source) → bool`
- **fn** [[scripts-codebase_graph-py-scan_file]]`(path) → tuple[FileNode, list[ClassNode], list[FunctionNode]]`
- **fn** [[scripts-codebase_graph-py-scan_codebase]]`(target_module) → CodebaseGraph`
- **fn** [[scripts-codebase_graph-py-scan_non_python]]`(graph, target_module) → None`
- **fn** [[scripts-codebase_graph-py-export_json]]`(graph) → Path`
- **fn** [[scripts-codebase_graph-py-_slug]]`(name) → str`
- **fn** [[scripts-codebase_graph-py-_wikilink]]`(node_id) → str`
- **fn** [[scripts-codebase_graph-py-_truncate_docstring]]`(doc, max_lines) → str`
- **fn** [[scripts-codebase_graph-py-_build_reverse_index]]`(graph) → dict[str, list[Edge]]`
- **fn** [[scripts-codebase_graph-py-_build_forward_index]]`(graph) → dict[str, list[Edge]]`
- **fn** [[scripts-codebase_graph-py-generate_obsidian]]`(graph) → None`
- **fn** [[scripts-codebase_graph-py-_generate_index]]`(graph, modules, total_pages) → None`
- **fn** [[scripts-codebase_graph-py-_generate_cloud]]`(graph) → None`
- **fn** [[scripts-codebase_graph-py-main]]`() → None`

## Import Statements

```python
from __future__ import annotations
import argparse
import ast
import json
import os
import re
import sys
import textwrap
from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
```
