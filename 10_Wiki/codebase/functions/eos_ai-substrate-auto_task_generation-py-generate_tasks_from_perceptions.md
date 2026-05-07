---
type: codebase-function
file: eos_ai/substrate/auto_task_generation.py
line: 55
generated: 2026-05-07
---

# generate_tasks_from_perceptions

**File:** [[eos_ai-substrate-auto_task_generation-py]] | **Line:** 55
**Signature:** `generate_tasks_from_perceptions(perceptions) → list[object]`

Generate tasks from actionable perception records.

Rules:
- Only generate tasks from WARNING and CRITICAL perceptions.
- INFO perceptions are logged but not actionable.
...

## Calls

- [[eos_ai-substrate-auto_task_generation-py-_candidate_title]]
- [[eos_ai-substrate-auto_task_generation-py-_log]]
- [[eos_ai-substrate-perception-py-PerceptionStore-all]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-_log]]

## Called By

- [[eos_ai-substrate-auto_task_generation-py-run_perception_cycle]]
