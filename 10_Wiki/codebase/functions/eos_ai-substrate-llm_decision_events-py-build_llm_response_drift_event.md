---
type: codebase-function
file: eos_ai/substrate/llm_decision_events.py
line: 175
generated: 2026-05-07
---

# build_llm_response_drift_event

**File:** [[eos_ai-substrate-llm_decision_events-py]] | **Line:** 175
**Signature:** `build_llm_response_drift_event(prompt_hash, response_hash_a, response_hash_b, session_name, decision_phase, run_id) → SchedulerEvent`

Emitted when same prompt_hash produces different response_hash.

Drift detection only applies within identical execution context.
prompt_hash is a composite of (prompt, model, temperature,
config_version, registry_version).  Different prompt_hash values
...

## Called By

- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_check_drift]]
