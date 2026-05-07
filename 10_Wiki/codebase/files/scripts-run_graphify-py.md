---
type: codebase-file
path: scripts/run_graphify.py
module: scripts.run_graphify
lines: 526
size: 19538
tags: [entry-point]
generated: 2026-05-07
---

# scripts/run_graphify.py

> **ENTRY POINT** — Contains `if __name__` or server start.

run_graphify.py — Pluggable enrichment layer (Graphify adapter).

Produces data/graphify_overlay.json — an additive enrichment over the
primary codebase_graph.json. NEVER writes to the primary graph.

...

**Lines:** 526 | **Size:** 19,538 bytes

## Contains

- **fn** [[scripts-run_graphify-py-_probe_external]]`() → tuple[str | None, str | None]`
- **fn** [[scripts-run_graphify-py-_run_external_binary]]`() → dict[str, Any] | None`
- **fn** [[scripts-run_graphify-py-_run_external_module]]`() → dict[str, Any] | None`
- **fn** [[scripts-run_graphify-py-_load_graph]]`() → dict[str, Any]`
- **fn** [[scripts-run_graphify-py-_file_import_graph]]`(graph) → dict[str, set[str]]`
- **fn** [[scripts-run_graphify-py-_label_propagation]]`(adj) → dict[str, str]`
- **fn** [[scripts-run_graphify-py-_clusters_from_labels]]`(labels) → list[dict[str, Any]]`
- **fn** [[scripts-run_graphify-py-_tokenize_doc]]`(text) → set[str]`
- **fn** [[scripts-run_graphify-py-_co_occurrence_edges]]`(graph) → list[dict[str, Any]]`
- **fn** [[scripts-run_graphify-py-_cross_language_edges]]`(graph) → list[dict[str, Any]]`
- **fn** [[scripts-run_graphify-py-_build_internal]]`() → dict[str, Any]`
- **fn** [[scripts-run_graphify-py-_build_external]]`(invocation, version) → dict[str, Any] | None`
- **fn** [[scripts-run_graphify-py-run]]`() → dict[str, Any]`
- **fn** [[scripts-run_graphify-py-_print_stats]]`() → int`
- **fn** [[scripts-run_graphify-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from collections import defaultdict
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
```
