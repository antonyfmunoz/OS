---
type: codebase-class
file: eos_ai/substrate/task_pipeline.py
line: 205
generated: 2026-05-07
---

# TaskPipeline

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 205

An ordered sequence of steps that execute a task.

## Methods

- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-new]]`(task_id, title, agent_owner, steps) → 'TaskPipeline'` — Create a new TaskPipeline with generated ID and current timestamps.
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-current_step]]`() → Optional[PipelineStep]` — Return the step at current_step_index, or None if out of bounds.
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-completed_steps]]`() → list[PipelineStep]` — Return all steps with COMPLETED status.
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-failed_steps]]`() → list[PipelineStep]` — Return all steps with FAILED status.
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-is_terminal]]`() → bool` — True if pipeline is in a terminal state (COMPLETED, FAILED).
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-to_dict]]`() → dict` — Return a JSON-safe dict.
- [[eos_ai-substrate-task_pipeline-py-TaskPipeline-from_dict]]`(d) → 'TaskPipeline'` — Deserialize from a dict with safe defaults.

## Decorators

- `@dataclass`
