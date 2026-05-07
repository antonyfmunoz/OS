---
type: codebase-function
file: eos_ai/substrate/auto_task_generation.py
line: 137
generated: 2026-05-07
---

# run_perception_cycle

**File:** [[eos_ai-substrate-auto_task_generation-py]] | **Line:** 137
**Signature:** `run_perception_cycle() → dict`

Run a full perception-to-task cycle.

Steps:
1. Collect all perceptions via collect_all_perceptions().
2. Persist each to PerceptionStore (dedup by fingerprint).
...

## Calls

- [[eos_ai-substrate-auto_task_generation-py-_log]]
- [[eos_ai-substrate-auto_task_generation-py-generate_tasks_from_perceptions]]
- [[eos_ai-substrate-perception-py-PerceptionStore-default]]
- [[eos_ai-substrate-perception-py-PerceptionStore-has_fingerprint]]
- [[eos_ai-substrate-perception-py-PerceptionStore-put]]
- [[eos_ai-substrate-perception-py-_log]]
- [[eos_ai-substrate-perception-py-collect_all_perceptions]]
