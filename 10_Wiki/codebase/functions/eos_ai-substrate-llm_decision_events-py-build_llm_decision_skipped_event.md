---
type: codebase-function
file: eos_ai/substrate/llm_decision_events.py
line: 150
generated: 2026-05-07
---

# build_llm_decision_skipped_event

**File:** [[eos_ai-substrate-llm_decision_events-py]] | **Line:** 150
**Signature:** `build_llm_decision_skipped_event(reason, state_hash, session_name, decision_phase, run_id) → SchedulerEvent`

Emitted when the LLM layer is bypassed for any reason.

## Called By

- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-evaluate]]
