---
type: codebase-file
path: eos_ai/substrate/llm_decision_events.py
module: eos_ai.substrate.llm_decision_events
lines: 206
size: 6085
generated: 2026-05-07
---

# eos_ai/substrate/llm_decision_events.py

Event construction helpers for the LLM planning layer.

Centralises observability event construction for:
    - LLM_DECISION_REQUESTED
    - LLM_DECISION_RECEIVED
...

**Lines:** 206 | **Size:** 6,085 bytes

## Depends On

- [[eos_ai-substrate-event_scheduler-py]]

## Used By

- [[eos_ai-substrate-llm_replay-py]]

## Contains

- **fn** [[eos_ai-substrate-llm_decision_events-py-build_llm_decision_requested_event]]`(state_hash, prompt_hash, active_intent_ids, session_name, decision_phase, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-llm_decision_events-py-build_llm_decision_received_event]]`(proposal_id, prompt_hash, response_hash, event_count, latency_ms, session_name, decision_phase, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-llm_decision_events-py-build_llm_decision_accepted_event]]`(proposal_id, emitted_event_count, selection_policy, session_name, decision_phase, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-llm_decision_events-py-build_llm_decision_rejected_event]]`(proposal_id, prompt_hash, rejection_reason, rejected_event_count, session_name, decision_phase, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-llm_decision_events-py-build_llm_decision_skipped_event]]`(reason, state_hash, session_name, decision_phase, run_id) → SchedulerEvent`
- **fn** [[eos_ai-substrate-llm_decision_events-py-build_llm_response_drift_event]]`(prompt_hash, response_hash_a, response_hash_b, session_name, decision_phase, run_id) → SchedulerEvent`

## Import Statements

```python
from __future__ import annotations
from eos_ai.substrate.event_scheduler import SchedulerEvent
```
