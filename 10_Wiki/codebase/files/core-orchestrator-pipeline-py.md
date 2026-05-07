---
type: codebase-file
path: core/orchestrator/pipeline.py
module: core.orchestrator.pipeline
lines: 277
size: 8965
generated: 2026-05-07
---

# core/orchestrator/pipeline.py

Pipeline — sequential composition of Control Plane actions.

A Pipeline is an ordered list of Steps. Each Step either:
  - wraps a direct call to `run_action()` via an ActionStep descriptor, OR
  - wraps a plain Python callable that receives the shared context dict
...

**Lines:** 277 | **Size:** 8,965 bytes

## Depends On

- [[core-action_system-control_plane-py]]
- [[core-action_system-logging-py]]

## Used By

- [[core-execution_bridge-py]]
- [[core-feedback-py]]
- [[core-objective-py]]
- [[core-router-py]]

## Contains

- **class** [[core-orchestrator-pipeline-py-ActionStep]] — 0 methods
- **class** [[core-orchestrator-pipeline-py-FuncStep]] — 0 methods
- **class** [[core-orchestrator-pipeline-py-Pipeline]] — 0 methods
- **class** [[core-orchestrator-pipeline-py-StepOutcome]] — 0 methods
- **class** [[core-orchestrator-pipeline-py-PipelineResult]] — 1 methods
- **fn** [[core-orchestrator-pipeline-py-_run_action_step]]`(step, context) → StepOutcome`
- **fn** [[core-orchestrator-pipeline-py-_run_func_step]]`(step, context) → StepOutcome`
- **fn** [[core-orchestrator-pipeline-py-run_pipeline]]`(pipeline, context) → PipelineResult`

## Import Statements

```python
from __future__ import annotations
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
from core.action_system.control_plane import run_action
from core.action_system.logging import log_decision
```
