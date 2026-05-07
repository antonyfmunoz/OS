---
type: codebase-function
file: eos_ai/substrate/pipeline_execution.py
line: 676
generated: 2026-05-07
---

# get_pipeline_summary

**File:** [[eos_ai-substrate-pipeline_execution-py]] | **Line:** 676
**Signature:** `get_pipeline_summary() → dict`

Build a summary dict for briefings.

Returns:
    {
        "active_pipelines": int,
...

## Calls

- [[eos_ai-substrate-task_pipeline-py-PipelineStore-all]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-by_status]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-default]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-current_step]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-is_terminal]]
