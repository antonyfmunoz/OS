---
type: codebase-function
file: eos_ai/substrate/task_pipeline.py
line: 259
generated: 2026-05-07
---

# TaskPipeline.current_step

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 259
**Signature:** `current_step() → Optional[PipelineStep]`

**Class:** [[eos_ai-substrate-task_pipeline-py-TaskPipeline]]

Return the step at current_step_index, or None if out of bounds.

## Called By

- [[eos_ai-substrate-pipeline_execution-py-execute_pipeline]]
- [[eos_ai-substrate-pipeline_execution-py-format_blocked_summary]]
- [[eos_ai-substrate-pipeline_execution-py-format_pipeline_summary]]
- [[eos_ai-substrate-pipeline_execution-py-get_pipeline_summary]]
- [[eos_ai-substrate-pipeline_execution-py-resume_pipeline]]
