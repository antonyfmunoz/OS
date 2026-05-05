---
type: codebase-file
path: core/orchestrator/orchestrator.py
module: core.orchestrator.orchestrator
lines: 200
size: 6461
generated: 2026-04-12
---

# core/orchestrator/orchestrator.py

Orchestrator — execution coordinator for named workflows.

The Orchestrator is a thin registry + dispatcher:
  - `register_workflow(name, pipeline_or_callable)`
  - `run_workflow(name, context=...)`
...

**Lines:** 200 | **Size:** 6,461 bytes

## Depends On

- [[core-action_system-logging-py]]

## Used By

- [[scripts-orchestrator_loop-py]]
- [[scripts-orchestrator_status-py]]

## Contains

- **class** [[core-orchestrator-orchestrator-py-WorkflowRecord]] — 0 methods
- **class** [[core-orchestrator-orchestrator-py-Orchestrator]] — 7 methods
- **fn** [[core-orchestrator-orchestrator-py-default_orchestrator]]`() → Orchestrator`

## Import Statements

```python
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from threading import Lock
from typing import Any
from typing import Callable
from typing import Union
from core.action_system.logging import log_decision
from pipeline import Pipeline
from pipeline import PipelineResult
from pipeline import run_pipeline
```
