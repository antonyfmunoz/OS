---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 950
generated: 2026-05-07
---

# collect_all_perceptions

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 950
**Signature:** `collect_all_perceptions() → list[PerceptionRecord]`

Run all collectors and return combined results.

Never raises — each collector is called independently and failures
are logged but do not prevent other collectors from running.

## Calls

- [[eos_ai-substrate-perception-py-_log]]

## Called By

- [[eos_ai-substrate-auto_task_generation-py-run_perception_cycle]]
