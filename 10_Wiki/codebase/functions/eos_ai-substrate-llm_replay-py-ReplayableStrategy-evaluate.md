---
type: codebase-function
file: eos_ai/substrate/llm_replay.py
line: 315
generated: 2026-05-07
---

# ReplayableStrategy.evaluate

**File:** [[eos_ai-substrate-llm_replay-py]] | **Line:** 315
**Signature:** `evaluate(state) → DecisionOutput | None`

**Class:** [[eos_ai-substrate-llm_replay-py-ReplayableStrategy]]

Evaluate state via the LLM planning layer.

Implements DecisionStrategy protocol.  Returns terminal sentinel
on success, None on any failure (silent fallback to planner).

## Calls

- [[eos_ai-substrate-event_scheduler-py-EventScheduler-emit]]
- [[eos_ai-substrate-llm_decision_events-py-build_llm_decision_skipped_event]]
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-get]]
- [[eos_ai-substrate-llm_planner-py-LLMPlannerConfig-is_enabled_for_intent]]
- [[eos_ai-substrate-llm_planner-py-_canonical_json]]
- [[eos_ai-substrate-llm_planner-py-_sha256_prefix]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_get_key_lock]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_hit]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_miss]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_store_get]]
