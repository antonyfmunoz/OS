---
type: codebase-function
file: eos_ai/substrate/pipeline_execution.py
line: 608
generated: 2026-05-07
---

# resume_pipeline

**File:** [[eos_ai-substrate-pipeline_execution-py]] | **Line:** 608
**Signature:** `resume_pipeline(pipeline_id, session) → TaskPipeline`

Resume a pipeline from its current step.

Does not restart completed steps. Handles PAUSED, WAITING_ON_OPERATOR,
and IN_PROGRESS pipelines.

...

## Calls

- [[eos_ai-substrate-pipeline_execution-py-_log]]
- [[eos_ai-substrate-pipeline_execution-py-_utcnow]]
- [[eos_ai-substrate-pipeline_execution-py-execute_pipeline]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-default]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-get]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-put]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-current_step]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-is_terminal]]
- [[eos_ai-substrate-task_pipeline-py-_log]]
- [[eos_ai-substrate-task_pipeline-py-_utcnow]]
