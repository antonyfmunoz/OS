---
type: codebase-class
file: eos_ai/substrate/task_pipeline.py
line: 339
generated: 2026-05-07
---

# PipelineStore

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 339

Durable, thread-safe, singleton store for TaskPipeline records.

Dual-layer: in-memory dict + substrate.storage.
Best-effort persistence — flush failures log, never raise.
Bounded — prunes oldest completed pipelines when count exceeds limit.

## Methods

- [[eos_ai-substrate-task_pipeline-py-PipelineStore-__init__]]`() → None` — 
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-_load]]`() → None` — 
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-_flush]]`() → None` — 
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-_prune_if_needed]]`() → None` — Remove oldest completed pipelines if store exceeds limit.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-get]]`(pipeline_id) → Optional[TaskPipeline]` — Return a pipeline by ID, or None.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-get_by_task_id]]`(task_id) → Optional[TaskPipeline]` — Return the pipeline linked to a task, or None.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-put]]`(pipeline) → None` — Insert or update a pipeline. Flushes to storage.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-all]]`() → list[TaskPipeline]` — Return all pipelines, ordered by created_at ascending.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-by_status]]`(status) → list[TaskPipeline]` — Return pipelines with the given status.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-active_pipelines]]`() → list[TaskPipeline]` — Return pipelines in non-terminal states.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-count_by_status]]`() → dict[str, int]` — Return {status_value: count} summary.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-default]]`() → 'PipelineStore'` — Return the process-level singleton.
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-reset_default_for_tests]]`() → None` — Tear down singleton for test isolation.
