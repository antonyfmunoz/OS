---
type: codebase-function
file: eos_ai/substrate/llm_decision_events.py
line: 60
generated: 2026-05-07
---

# build_llm_decision_received_event

**File:** [[eos_ai-substrate-llm_decision_events-py]] | **Line:** 60
**Signature:** `build_llm_decision_received_event(proposal_id, prompt_hash, response_hash, event_count, latency_ms, session_name, decision_phase, run_id) → SchedulerEvent`

Emitted when LLM response arrives and is parsed.

## Called By

- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_miss]]
