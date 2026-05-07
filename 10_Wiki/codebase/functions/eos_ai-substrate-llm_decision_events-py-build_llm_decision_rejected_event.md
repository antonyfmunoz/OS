---
type: codebase-function
file: eos_ai/substrate/llm_decision_events.py
line: 120
generated: 2026-05-07
---

# build_llm_decision_rejected_event

**File:** [[eos_ai-substrate-llm_decision_events-py]] | **Line:** 120
**Signature:** `build_llm_decision_rejected_event(proposal_id, prompt_hash, rejection_reason, rejected_event_count, session_name, decision_phase, run_id) → SchedulerEvent`

Emitted when validation rejects the proposal (partial or full).

## Called By

- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_miss]]
