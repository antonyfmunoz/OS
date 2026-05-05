---
type: codebase-file
path: core/tool_mastery_manager/maintenance.py
module: core.tool_mastery_manager.maintenance
lines: 61
size: 1990
generated: 2026-04-12
---

# core/tool_mastery_manager/maintenance.py

Maintenance flows for the Tool Mastery Manager.

Thin compositions over coverage + ensure. These exist so the ongoing
upkeep path (refresh stale, repair invalid, audit all) is a first-class
Manager surface rather than a tangle of shell commands.

**Lines:** 61 | **Size:** 1,990 bytes

## Used By

- [[scripts-tool_mastery_manager-py]]

## Contains

- **fn** [[core-tool_mastery_manager-maintenance-py-refresh_stale]]`() → list[dict]`
- **fn** [[core-tool_mastery_manager-maintenance-py-repair_invalid]]`() → list[dict]`
- **fn** [[core-tool_mastery_manager-maintenance-py-audit_all]]`() → dict`

## Import Statements

```python
from __future__ import annotations
from backlog import build_backlog
from coverage import evaluate_coverage
from discovery import discover_all
from ensure import ensure_mastery
from models import CoverageStatus
```
