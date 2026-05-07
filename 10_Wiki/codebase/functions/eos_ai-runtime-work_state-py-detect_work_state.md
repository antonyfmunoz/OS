---
type: codebase-function
file: eos_ai/runtime/work_state.py
line: 190
generated: 2026-05-07
---

# detect_work_state

**File:** [[eos_ai-runtime-work_state-py]] | **Line:** 190
**Signature:** `detect_work_state() → WorkState`

Snapshot current work state and compute idle delay.

## Calls

- [[eos_ai-runtime-work_state-py-_compute_idle_delay]]
- [[eos_ai-runtime-work_state-py-_measure_pressure]]
- [[eos_ai-runtime-work_state-py-has_recent_signal]]

## Called By

- [[eos_ai-runtime-work_state-py-get_idle_delay]]
