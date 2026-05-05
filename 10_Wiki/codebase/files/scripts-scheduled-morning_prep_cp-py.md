---
type: codebase-file
path: scripts/scheduled/morning_prep_cp.py
module: scripts.scheduled.morning_prep_cp
lines: 83
size: 2888
tags: [entry-point]
generated: 2026-04-12
---

# scripts/scheduled/morning_prep_cp.py

> **ENTRY POINT** — Contains `if __name__` or server start.

morning_prep_cp.py — Control Plane wrapper for morning_prep.sh.

This is the Control Plane migration of the morning_prep workflow.
Cron (or the operator) calls this Python entry instead of the raw
bash script, and the underlying .sh runs as a `run_script` action:
...

**Lines:** 83 | **Size:** 2,888 bytes

## Depends On

- [[core-orchestrator-steps-py]]

## Contains

- **fn** [[scripts-scheduled-morning_prep_cp-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import sys
from datetime import datetime
from datetime import timezone
from core.orchestrator.steps import ScriptWorkflowSpec
from core.orchestrator.steps import run_script_workflow
```
