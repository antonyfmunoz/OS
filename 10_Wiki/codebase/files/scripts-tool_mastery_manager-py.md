---
type: codebase-file
path: scripts/tool_mastery_manager.py
module: scripts.tool_mastery_manager
lines: 216
size: 8074
tags: [entry-point]
generated: 2026-04-12
---

# scripts/tool_mastery_manager.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Tool Mastery Manager — CLI.

Thin wrapper over the `core.tool_mastery_manager` package. The package
is the source of truth; this file is deliberately shallow so changing
Manager behaviour never requires CLI surgery.
...

**Lines:** 216 | **Size:** 8,074 bytes

## Depends On

- [[core-tool_mastery_manager-backlog-py]]
- [[core-tool_mastery_manager-coverage-py]]
- [[core-tool_mastery_manager-ensure-py]]
- [[core-tool_mastery_manager-maintenance-py]]
- [[core-tool_mastery_manager-models-py]]

## Contains

- **fn** [[scripts-tool_mastery_manager-py-_emit]]`(payload, as_json, fallback_lines) → None`
- **fn** [[scripts-tool_mastery_manager-py-cmd_ensure]]`(args) → int`
- **fn** [[scripts-tool_mastery_manager-py-cmd_status]]`(args) → int`
- **fn** [[scripts-tool_mastery_manager-py-cmd_scan]]`(args) → int`
- **fn** [[scripts-tool_mastery_manager-py-cmd_backlog]]`(args) → int`
- **fn** [[scripts-tool_mastery_manager-py-cmd_bootstrap]]`(args) → int`
- **fn** [[scripts-tool_mastery_manager-py-cmd_refresh_stale]]`(args) → int`
- **fn** [[scripts-tool_mastery_manager-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from core.tool_mastery_manager.backlog import backlog_report
from core.tool_mastery_manager.backlog import bootstrap
from core.tool_mastery_manager.coverage import evaluate_coverage
from core.tool_mastery_manager.ensure import ensure_mastery
from core.tool_mastery_manager.maintenance import audit_all
from core.tool_mastery_manager.maintenance import refresh_stale
from core.tool_mastery_manager.models import CoverageStatus
```
