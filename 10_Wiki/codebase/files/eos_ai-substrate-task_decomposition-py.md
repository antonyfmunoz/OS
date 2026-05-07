---
type: codebase-file
path: eos_ai/substrate/task_decomposition.py
module: eos_ai.substrate.task_decomposition
lines: 225
size: 7623
generated: 2026-05-07
---

# eos_ai/substrate/task_decomposition.py

Deterministic task decomposition — breaks tasks into ordered pipeline steps.

Uses keyword heuristics (zero LLM cost) to infer an agent role and select
a template pipeline. Three templates for v1:

...

**Lines:** 225 | **Size:** 7,623 bytes

## Depends On

- [[eos_ai-substrate-task_pipeline-py]]

## Contains

- **fn** [[eos_ai-substrate-task_decomposition-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-task_decomposition-py-infer_agent_role]]`(task) → PipelineAgentRole`
- **fn** [[eos_ai-substrate-task_decomposition-py-_builder_steps]]`(role) → list[PipelineStep]`
- **fn** [[eos_ai-substrate-task_decomposition-py-_product_steps]]`(role) → list[PipelineStep]`
- **fn** [[eos_ai-substrate-task_decomposition-py-_ceo_portfolio_steps]]`(role) → list[PipelineStep]`
- **fn** [[eos_ai-substrate-task_decomposition-py-decompose_task]]`(task) → TaskPipeline`

## Import Statements

```python
from __future__ import annotations
import re
import sys
from typing import TYPE_CHECKING
from eos_ai.substrate.task_pipeline import PipelineAgentRole
from eos_ai.substrate.task_pipeline import PipelineStep
from eos_ai.substrate.task_pipeline import PipelineStatus
from eos_ai.substrate.task_pipeline import StepStatus
from eos_ai.substrate.task_pipeline import TaskPipeline
```
