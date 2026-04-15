---
type: codebase-file
path: scripts/scheduled/nightly_consolidation_cp.py
module: scripts.scheduled.nightly_consolidation_cp
lines: 111
size: 4087
tags: [entry-point]
generated: 2026-04-12
---

# scripts/scheduled/nightly_consolidation_cp.py

> **ENTRY POINT** — Contains `if __name__` or server start.

nightly_consolidation_cp.py — Control Plane wrapper for nightly_consolidation.sh.

Second real workflow routed through `core.action_system.run_action`.
Mirrors the shape of `morning_prep_cp.py` — this is deliberate, since
part of Phase 3's goal is proving the migration pattern is boringly
...

**Lines:** 111 | **Size:** 4,087 bytes

## Depends On

- [[core-orchestrator-steps-py]]

## Contains

- **fn** [[scripts-scheduled-nightly_consolidation_cp-py-main]]`() → int`

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
