---
type: codebase-function
file: eos_ai/substrate/task_pipeline.py
line: 123
generated: 2026-05-07
---

# PipelineStep.new

**File:** [[eos_ai-substrate-task_pipeline-py]] | **Line:** 123
**Signature:** `new(title, step_index, agent_role) → 'PipelineStep'`

**Class:** [[eos_ai-substrate-task_pipeline-py-PipelineStep]]

Create a new PipelineStep with generated ID and current timestamp.

## Calls

- [[eos_ai-substrate-task_pipeline-py-_new_step_id]]
- [[eos_ai-substrate-task_pipeline-py-_utcnow]]

## Called By

- [[eos_ai-substrate-task_decomposition-py-_builder_steps]]
- [[eos_ai-substrate-task_decomposition-py-_ceo_portfolio_steps]]
- [[eos_ai-substrate-task_decomposition-py-_product_steps]]
- [[eos_ai-substrate-task_decomposition-py-decompose_task]]

## Decorators

- `@classmethod`
