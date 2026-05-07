---
type: codebase-function
file: eos_ai/substrate/task_pipeline.py
line: 412
generated: 2026-05-07
---

# PipelineStore.put

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 412
**Signature:** `put(pipeline) → None`

**Class:** [[eos_ai-substrate-task_pipeline-py-PipelineStore]]

Insert or update a pipeline. Flushes to storage.

## Calls

- [[eos_ai-substrate-task_pipeline-py-PipelineStore-_flush]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-_prune_if_needed]]
- [[eos_ai-substrate-task_pipeline-py-_utcnow]]

## Called By

- [[eos_ai-substrate-pipeline_execution-py-execute_pipeline]]
- [[eos_ai-substrate-pipeline_execution-py-resume_pipeline]]
- [[eos_ai-substrate-pipeline_execution-py-retry_step]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-_flush]]
