---
type: codebase-file
path: eos_ai/substrate/task_pipeline.py
module: eos_ai.substrate.task_pipeline
lines: 481
size: 18081
generated: 2026-05-07
---

# eos_ai/substrate/task_pipeline.py

Task pipeline data model — ordered multi-step execution for tasks.

Decomposes tasks into linear pipelines of typed steps, each bound to an
agent role.  Pipelines persist through the same dual-layer storage used by
TaskStore (in-memory + substrate.storage) and survive process restarts.
...

**Lines:** 481 | **Size:** 18,081 bytes

## Used By

- [[eos_ai-substrate-pipeline_execution-py]]
- [[eos_ai-substrate-task_decomposition-py]]

## Contains

- **class** [[eos_ai-substrate-task_pipeline-py-PipelineStatus]] — 0 methods
- **class** [[eos_ai-substrate-task_pipeline-py-StepStatus]] — 0 methods
- **class** [[eos_ai-substrate-task_pipeline-py-PipelineAgentRole]] — 0 methods
- **class** [[eos_ai-substrate-task_pipeline-py-PipelineStep]] — 3 methods
- **class** [[eos_ai-substrate-task_pipeline-py-TaskPipeline]] — 7 methods
- **class** [[eos_ai-substrate-task_pipeline-py-PipelineStore]] — 13 methods
- **fn** [[eos_ai-substrate-task_pipeline-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-task_pipeline-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-task_pipeline-py-_new_pipeline_id]]`() → str`
- **fn** [[eos_ai-substrate-task_pipeline-py-_new_step_id]]`() → str`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional
```
