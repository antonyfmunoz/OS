---
type: codebase-file
path: core/orchestrator/workflows.py
module: core.orchestrator.workflows
lines: 125
size: 4924
generated: 2026-05-07
---

# core/orchestrator/workflows.py

Workflow registry — wires existing Control Plane workflows into the orchestrator.

The three migrated CP workflows (morning_prep_cp, nightly_consolidation_cp,
weekly_review_cp) already call `run_action()` internally with idempotency
keys, so the orchestrator treats each one as a callable workflow that
...

**Lines:** 125 | **Size:** 4,924 bytes

## Used By

- [[scripts-orchestrator_loop-py]]
- [[scripts-orchestrator_status-py]]

## Contains

- **fn** [[core-orchestrator-workflows-py-_wrap_main]]`(module_path)`
- **fn** [[core-orchestrator-workflows-py-register_default_workflows]]`(orch) → list[str]`

## Import Statements

```python
from __future__ import annotations
import importlib
import sys
from typing import Any
from handlers import handle_action_failed
from handlers import handle_action_retry_requested
from handlers import handle_deferred_stale
from orchestrator import Orchestrator
from orchestrator import default_orchestrator
from signals import register_handler
```
