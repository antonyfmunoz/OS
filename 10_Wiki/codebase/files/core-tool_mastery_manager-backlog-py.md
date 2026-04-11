---
type: codebase-file
path: core/tool_mastery_manager/backlog.py
module: core.tool_mastery_manager.backlog
lines: 189
size: 6109
generated: 2026-04-11
---

# core/tool_mastery_manager/backlog.py

Backlog / bootstrap flow.

`backlog()` runs full discovery + coverage evaluation and returns the
prioritised worklist of non-READY tools. `bootstrap()` is the fresh-
environment path: it calls `backlog()` then invokes `ensure_mastery`
...

**Lines:** 189 | **Size:** 6,109 bytes

## Used By

- [[scripts-tool_mastery_manager-py]]

## Contains

- **class** [[core-tool_mastery_manager-backlog-py-BacklogEntry]] — 1 methods
- **fn** [[core-tool_mastery_manager-backlog-py-_iter_discovered]]`(explicit) → list[ToolRef]`
- **fn** [[core-tool_mastery_manager-backlog-py-build_backlog]]`() → list[BacklogEntry]`
- **fn** [[core-tool_mastery_manager-backlog-py-_write_report]]`(entries, kind) → dict[str, str]`
- **fn** [[core-tool_mastery_manager-backlog-py-backlog_report]]`() → dict`
- **fn** [[core-tool_mastery_manager-backlog-py-bootstrap]]`() → dict`

## Import Statements

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Iterable
from coverage import evaluate_coverage
from discovery import discover_all
from ensure import ensure_mastery
from models import CoverageReport
from models import CoverageStatus
from models import EnsureResult
from models import ToolRef
from paths import BACKLOG_DIR
```
