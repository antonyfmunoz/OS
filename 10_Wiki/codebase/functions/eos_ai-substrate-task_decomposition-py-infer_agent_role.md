---
type: codebase-function
file: eos_ai/substrate/task_decomposition.py
line: 66
generated: 2026-05-07
---

# infer_agent_role

**File:** [[eos_ai-substrate-task_decomposition-py]] | **Line:** 66
**Signature:** `infer_agent_role(task) → PipelineAgentRole`

Infer the pipeline agent role from task title + description.

Priority order: builder > portfolio > ceo > product > general.
Uses combined text of title + description for matching.

## Called By

- [[eos_ai-substrate-task_decomposition-py-decompose_task]]
