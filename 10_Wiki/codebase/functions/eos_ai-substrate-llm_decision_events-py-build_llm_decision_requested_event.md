---
type: codebase-function
file: eos_ai/substrate/llm_decision_events.py
line: 32
generated: 2026-05-07
---

# build_llm_decision_requested_event

**File:** [[eos_ai-substrate-llm_decision_events-py]] | **Line:** 32
**Signature:** `build_llm_decision_requested_event(state_hash, prompt_hash, active_intent_ids, session_name, decision_phase, run_id) → SchedulerEvent`

Emitted when the LLM is about to be called.

## Called By

- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_miss]]
