---
type: codebase-function
file: eos_ai/substrate/task_decomposition.py
line: 185
generated: 2026-05-07
---

# decompose_task

**File:** [[eos_ai-substrate-task_decomposition-py]] | **Line:** 185
**Signature:** `decompose_task(task) → TaskPipeline`

Decompose a task into a linear pipeline of typed steps.

Uses deterministic keyword matching to select the template.
Step 0 is always READY; subsequent steps start as PENDING.
The pipeline starts in READY status.
...

## Calls

- [[eos_ai-substrate-task_decomposition-py-_log]]
- [[eos_ai-substrate-task_decomposition-py-infer_agent_role]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStep-new]]
- [[eos_ai-substrate-task_pipeline-py-PipelineStore-get]]
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-new]]
- [[eos_ai-substrate-task_pipeline-py-_log]]
