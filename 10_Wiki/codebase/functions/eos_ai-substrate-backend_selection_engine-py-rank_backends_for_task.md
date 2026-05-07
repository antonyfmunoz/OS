---
type: codebase-function
file: eos_ai/substrate/backend_selection_engine.py
line: 110
generated: 2026-05-07
---

# rank_backends_for_task

**File:** [[eos_ai-substrate-backend_selection_engine-py]] | **Line:** 110
**Signature:** `rank_backends_for_task(task, profiles) → list[BackendProfile]`

Rank backends by fitness for task.

## Calls

- [[eos_ai-substrate-backend_selection_engine-py-_score_backend]]
- [[eos_ai-substrate-backend_selection_engine-py-filter_backends_by_policy]]

## Called By

- [[eos_ai-substrate-backend_selection_engine-py-select_best_backend]]
