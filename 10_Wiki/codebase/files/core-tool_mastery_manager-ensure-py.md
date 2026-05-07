---
type: codebase-file
path: core/tool_mastery_manager/ensure.py
module: core.tool_mastery_manager.ensure
lines: 173
size: 6710
generated: 2026-05-07
---

# core/tool_mastery_manager/ensure.py

ensure_mastery — the primary entry point of the Tool Mastery Manager.

For a given tool slug this function:

    1. Evaluates current coverage via the composed TME utilities.
...

**Lines:** 173 | **Size:** 6,710 bytes

## Depends On

- [[core-action_system-control_plane-py]]

## Used By

- [[scripts-tool_mastery_manager-py]]

## Contains

- **fn** [[core-tool_mastery_manager-ensure-py-_scaffold]]`(slug) → tuple[bool, str]`
- **fn** [[core-tool_mastery_manager-ensure-py-_plan_for]]`(status, slug, reason) → ManagerPlan | None`
- **fn** [[core-tool_mastery_manager-ensure-py-_queue]]`(plan) → tuple[str | None, str | None]`
- **fn** [[core-tool_mastery_manager-ensure-py-ensure_mastery]]`(slug) → EnsureResult`

## Import Statements

```python
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from core.action_system.control_plane import run_action
from coverage import evaluate_coverage
from models import CoverageStatus
from models import EnsureResult
from models import ManagerPlan
from paths import RESEARCH_DISPATCHER
from paths import SCAFFOLD_SCRIPT
from paths import SKILLS_TOOLS_DIR
```
