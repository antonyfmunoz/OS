---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 263
generated: 2026-05-07
---

# PerceptionStore.all

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 263
**Signature:** `all() → list[PerceptionRecord]`

**Class:** [[eos_ai-substrate-perception-py-PerceptionStore]]

Return all records, sorted by observed_at descending (newest first).

## Called By

- [[eos_ai-substrate-auto_task_generation-py-generate_tasks_from_perceptions]]
- [[eos_ai-substrate-auto_task_generation-py-get_perception_summary]]
- [[eos_ai-substrate-perception-py-collect_live_session_perception]]
- [[eos_ai-substrate-perception-py-collect_local_control_perception]]
- [[eos_ai-substrate-perception-py-collect_node_status_perception]]
- [[eos_ai-substrate-perception-py-collect_pipeline_perception]]
