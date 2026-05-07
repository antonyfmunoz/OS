---
type: codebase-function
file: eos_ai/substrate/task_pipeline.py
line: 399
generated: 2026-05-07
---

# PipelineStore.get

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 399
**Signature:** `get(pipeline_id) → Optional[TaskPipeline]`

**Class:** [[eos_ai-substrate-task_pipeline-py-PipelineStore]]

Return a pipeline by ID, or None.

## Called By

- [[eos_ai-substrate-pipeline_execution-py-_execute_step]]
- [[eos_ai-substrate-pipeline_execution-py-_stream_step_event]]
- [[eos_ai-substrate-pipeline_execution-py-resume_pipeline]]
- [[eos_ai-substrate-pipeline_execution-py-retry_step]]
- [[eos_ai-substrate-task_decomposition-py-decompose_task]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStep-from_dict]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-_load]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-count_by_status]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-from_dict]]
