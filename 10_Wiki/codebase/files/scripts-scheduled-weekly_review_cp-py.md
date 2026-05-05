---
type: codebase-file
path: scripts/scheduled/weekly_review_cp.py
module: scripts.scheduled.weekly_review_cp
lines: 107
size: 3946
tags: [entry-point]
generated: 2026-04-12
---

# scripts/scheduled/weekly_review_cp.py

> **ENTRY POINT** — Contains `if __name__` or server start.

weekly_review_cp.py — Control Plane wrapper for weekly_review.sh.

Third workflow routed through `core.action_system.run_action`.
Mirrors `morning_prep_cp.py` and `nightly_consolidation_cp.py` — the
third instance is the one that proves the migration pattern is boring.
...

**Lines:** 107 | **Size:** 3,946 bytes

## Depends On

- [[core-orchestrator-steps-py]]

## Contains

- **fn** [[scripts-scheduled-weekly_review_cp-py-_idempotency_key]]`(now) → str`
- **fn** [[scripts-scheduled-weekly_review_cp-py-main]]`() → int`

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
