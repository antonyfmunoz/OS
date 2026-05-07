---
type: codebase-function
file: eos_ai/substrate/pipeline_execution.py
line: 365
generated: 2026-05-07
---

# execute_pipeline

**File:** [[eos_ai-substrate-pipeline_execution-py]] | **Line:** 365
**Signature:** `execute_pipeline(pipeline, session) → TaskPipeline`

Execute the current READY step of a pipeline.

If advance_all=True, continues executing steps until blocked, failed,
or completed. This is the mode used by overnight execution.

...

## Calls

- [[eos_ai-substrate-pipeline_execution-py-_execute_step]]
- [[eos_ai-substrate-pipeline_execution-py-_log]]
- [[eos_ai-substrate-pipeline_execution-py-_stream_step_event]]
- [[eos_ai-substrate-pipeline_execution-py-_utcnow]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-default]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-put]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-current_step]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-is_terminal]]
- [[eos_ai-substrate-task_pipeline-py-_log]]
- [[eos_ai-substrate-task_pipeline-py-_utcnow]]

## Called By

- [[eos_ai-substrate-pipeline_execution-py-resume_pipeline]]
- [[eos_ai-substrate-pipeline_execution-py-retry_step]]
