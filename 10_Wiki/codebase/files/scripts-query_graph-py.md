---
type: codebase-file
path: scripts/query_graph.py
module: scripts.query_graph
lines: 328
size: 13234
tags: [entry-point]
generated: 2026-04-11
---

# scripts/query_graph.py

> **ENTRY POINT** — Contains `if __name__` or server start.

query_graph.py — Retrieval layer over the EOS codebase knowledge graph.

Reads data/codebase_graph.json and answers structural questions without
opening source files. Use this BEFORE grepping or reading implementations.

...

**Lines:** 328 | **Size:** 13,234 bytes

## Used By

- [[scripts-build_palace-py]]
- [[scripts-session_bootstrap-py]]

## Contains

- **class** [[scripts-query_graph-py-GraphQuery]] — 12 methods
- **fn** [[scripts-query_graph-py-_print_list]]`(rows) → None`
- **fn** [[scripts-query_graph-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from collections import defaultdict
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Iterable
```
