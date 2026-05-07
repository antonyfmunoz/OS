---
type: codebase-function
file: eos_ai/substrate/pipeline_execution.py
line: 534
generated: 2026-05-07
---

# retry_step

**File:** [[eos_ai-substrate-pipeline_execution-py]] | **Line:** 534
**Signature:** `retry_step(pipeline_id, step_id, session) → TaskPipeline`

Retry a failed step without restarting the whole pipeline.

Resets the step to READY, increments its retry_count, and re-executes.
Pipeline transitions back to IN_PROGRESS if currently PAUSED/FAILED.

...

## Calls

- [[eos_ai-substrate-pipeline_execution-py-_log]]
- [[eos_ai-substrate-pipeline_execution-py-_utcnow]]
- [[eos_ai-substrate-pipeline_execution-py-execute_pipeline]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-default]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-get]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-put]]
- [[eos_ai-substrate-task_pipeline-py-_log]]
- [[eos_ai-substrate-task_pipeline-py-_utcnow]]
