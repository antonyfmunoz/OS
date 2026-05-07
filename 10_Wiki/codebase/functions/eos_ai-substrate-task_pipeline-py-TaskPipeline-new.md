---
type: codebase-function
file: eos_ai/substrate/task_pipeline.py
line: 229
generated: 2026-05-07
---

# TaskPipeline.new

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 229
**Signature:** `new(task_id, title, agent_owner, steps) → 'TaskPipeline'`

**Class:** [[eos_ai-substrate-task_pipeline-py-TaskPipeline]]

Create a new TaskPipeline with generated ID and current timestamps.

## Calls

- [[eos_ai-substrate-task_pipeline-py-_new_pipeline_id]]
- [[eos_ai-substrate-task_pipeline-py-_utcnow]]

## Called By

- [[eos_ai-substrate-task_decomposition-py-_builder_steps]]
- [[eos_ai-substrate-task_decomposition-py-_ceo_portfolio_steps]]
- [[eos_ai-substrate-task_decomposition-py-_product_steps]]
- [[eos_ai-substrate-task_decomposition-py-decompose_task]]

## Decorators

- `@classmethod`
