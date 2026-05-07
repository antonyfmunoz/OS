---
type: codebase-file
path: eos_ai/substrate/pipeline_execution.py
module: eos_ai.substrate.pipeline_execution
lines: 759
size: 28223
generated: 2026-05-07
---

# eos_ai/substrate/pipeline_execution.py

Pipeline execution engine — step-level execution, retry, and resume.

Executes pipelines one step at a time using the existing capability routing
and tmux-backed dispatch infrastructure. Steps transition through typed
states with step-level retry and operator-block detection.
...

**Lines:** 759 | **Size:** 28,223 bytes

## Depends On

- [[eos_ai-substrate-task_pipeline-py]]

## Contains

- **fn** [[eos_ai-substrate-pipeline_execution-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-pipeline_execution-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-pipeline_execution-py-_stream_step_event]]`(event_type_name, message) → None`
- **fn** [[eos_ai-substrate-pipeline_execution-py-_map_keyword_to_action]]`(keyword, rest, step) → Optional[tuple[str, dict]]`
- **fn** [[eos_ai-substrate-pipeline_execution-py-_detect_local_control_action]]`(step) → Optional[tuple[str, dict]]`
- **fn** [[eos_ai-substrate-pipeline_execution-py-_execute_local_control_step]]`(step, action_value, payload) → PipelineStep`
- **fn** [[eos_ai-substrate-pipeline_execution-py-_execute_step]]`(step, pipeline, session) → PipelineStep`
- **fn** [[eos_ai-substrate-pipeline_execution-py-execute_pipeline]]`(pipeline, session) → TaskPipeline`
- **fn** [[eos_ai-substrate-pipeline_execution-py-retry_step]]`(pipeline_id, step_id, session) → TaskPipeline`
- **fn** [[eos_ai-substrate-pipeline_execution-py-resume_pipeline]]`(pipeline_id, session) → TaskPipeline`
- **fn** [[eos_ai-substrate-pipeline_execution-py-get_pipeline_summary]]`() → dict`
- **fn** [[eos_ai-substrate-pipeline_execution-py-format_blocked_summary]]`(pipeline) → str`
- **fn** [[eos_ai-substrate-pipeline_execution-py-format_pipeline_summary]]`(pipeline) → str`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING
from typing import Optional
from eos_ai.substrate.task_pipeline import PipelineStatus
from eos_ai.substrate.task_pipeline import PipelineStore
from eos_ai.substrate.task_pipeline import PipelineStep
from eos_ai.substrate.task_pipeline import StepStatus
from eos_ai.substrate.task_pipeline import TaskPipeline
from eos_ai.substrate.task_pipeline import _MAX_STEP_RETRIES
```
