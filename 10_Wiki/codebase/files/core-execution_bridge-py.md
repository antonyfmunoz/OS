---
type: codebase-file
path: core/execution_bridge.py
module: core.execution_bridge
lines: 1314
size: 49473
generated: 2026-05-07
---

# core/execution_bridge.py

Execution Bridge — converts composed structures into executable pipelines.

This is the Phase 5 connection layer. It takes a ComposedStructure from
the composition engine and produces a Pipeline that runs through the
existing execution system (run_pipeline → ActionStep → run_action →
...

**Lines:** 1314 | **Size:** 49,473 bytes

## Depends On

- [[core-composer-py]]
- [[core-orchestrator-pipeline-py]]

## Contains

- **class** [[core-execution_bridge-py-LearningResult]] — 2 methods
- **class** [[core-execution_bridge-py-RoutedLearningResult]] — 2 methods
- **class** [[core-execution_bridge-py-RealityLoopResult]] — 2 methods
- **class** [[core-execution_bridge-py-FullRealityLoopResult]] — 1 methods
- **fn** [[core-execution_bridge-py-_build_icp_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_offer_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_workflow_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_channel_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_kpi_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_role_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_habit_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_energy_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_focus_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_identity_state_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_content_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_audience_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_platform_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-_build_engagement_pipeline]]`(structure) → list[ActionStep | FuncStep]`
- **fn** [[core-execution_bridge-py-build_pipeline]]`(structure) → Pipeline`
- **fn** [[core-execution_bridge-py-execute_composed]]`(structure, extra_context) → PipelineResult`
- **fn** [[core-execution_bridge-py-execute_with_learning]]`(structure, extra_context) → LearningResult`
- **fn** [[core-execution_bridge-py-execute_with_routing]]`(structure, constraints, extra_context) → RoutedLearningResult`
- **fn** [[core-execution_bridge-py-execute_with_reality_loop]]`(structure, constraints, extra_context) → RealityLoopResult`
- **fn** [[core-execution_bridge-py-execute_with_full_reality_loop]]`(structure, constraints, extra_context) → FullRealityLoopResult`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.composer import ComposedStructure
from core.orchestrator.pipeline import ActionStep
from core.orchestrator.pipeline import FuncStep
from core.orchestrator.pipeline import Pipeline
from core.orchestrator.pipeline import PipelineResult
from core.orchestrator.pipeline import run_pipeline
```
