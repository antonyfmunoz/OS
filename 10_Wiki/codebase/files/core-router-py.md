---
type: codebase-file
path: core/router.py
module: core.router
lines: 317
size: 10616
generated: 2026-05-07
---

# core/router.py

Resource Router — decomposes a pipeline into per-step capability assignments.

The router takes a ComposedStructure and produces an ExecutionPlan where
each step is assigned its own optimal capability.  This enables hybrid
execution: reasoning goes to Claude, formatting to local Python,
...

**Lines:** 317 | **Size:** 10,616 bytes

## Depends On

- [[core-capabilities-py]]
- [[core-composer-py]]
- [[core-matcher-py]]
- [[core-orchestrator-pipeline-py]]
- [[core-primitives-py]]

## Contains

- **class** [[core-router-py-RoutedStep]] — 1 methods
- **class** [[core-router-py-ExecutionPlan]] — 2 methods
- **class** [[core-router-py-RoutedExecutionResult]] — 2 methods
- **fn** [[core-router-py-_get_step_primitives]]`(step) → set[PrimitiveTag]`
- **fn** [[core-router-py-route_execution]]`(structure, constraints) → ExecutionPlan`
- **fn** [[core-router-py-execute_routed]]`(plan, extra_context) → RoutedExecutionResult`

## Import Statements

```python
from __future__ import annotations
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.capabilities import Capability
from core.capabilities import record_outcome
from core.composer import ComposedStructure
from core.matcher import CapabilitySelection
from core.matcher import match_for_step
from core.orchestrator.pipeline import ActionStep
from core.orchestrator.pipeline import FuncStep
from core.orchestrator.pipeline import Pipeline
from core.orchestrator.pipeline import PipelineResult
from core.orchestrator.pipeline import StepOutcome
from core.orchestrator.pipeline import run_pipeline
from core.primitives import PrimitiveTag
```
