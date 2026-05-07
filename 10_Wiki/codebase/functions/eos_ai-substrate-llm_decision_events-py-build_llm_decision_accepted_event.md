---
type: codebase-function
file: eos_ai/substrate/llm_decision_events.py
line: 93
generated: 2026-05-07
---

# build_llm_decision_accepted_event

**File:** [[eos_ai-substrate-llm_decision_events-py]] | **Line:** 93
**Signature:** `build_llm_decision_accepted_event(proposal_id, emitted_event_count, selection_policy, session_name, decision_phase, run_id) → SchedulerEvent`

Emitted when a proposal is validated and its events emitted.

## Called By

- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_miss]]
