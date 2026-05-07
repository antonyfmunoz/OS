---
type: codebase-class
file: eos_ai/substrate/llm_replay.py
line: 112
generated: 2026-05-07
---

# ReplayableStrategy

**File:** [[eos_ai-substrate-llm_replay-py]] | **Line:** 112

Determinism boundary.  Implements DecisionStrategy.

Wraps LLMPlanningStrategy and handles:
- Config enforcement at the entry point.
- Per-state-hash locking to prevent duplicate LLM calls.
...

## Methods

- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-__init__]]`(inner, scheduler, config, registry) → None` — 
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-name]]`() → str` — 
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-shutdown]]`() → None` — Shut down the executor cleanly.  Call on system teardown.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_get_key_lock]]`(state_hash) → threading.Lock` — Get or create a lock for a specific state_hash.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_store_get]]`(state_hash) → LLMDecisionRecord | None` — 
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_store_put]]`(state_hash, record) → None` — 
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_check_drift]]`(prompt_hash, response_hash, session_name) → None` — Detect response drift within identical execution context.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_emit_proposed_events]]`(events, proposal_id, session_name) → None` — Emit selected ProposedEvents as SchedulerEvents.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_build_sentinel]]`(proposal_id, state_hash, session_name, event_count) → DecisionOutput` — Build the terminal sentinel DecisionOutput.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-evaluate]]`(state) → DecisionOutput | None` — Evaluate state via the LLM planning layer.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_hit]]`(record, state_hash, session_name) → DecisionOutput | None` — Handle replay from stored record.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_revalidate_canonical]]`(canonical_json) → ValidationResult | None` — Re-validate a canonical proposal JSON against the current registry.
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_miss]]`(canonical_state, state_hash, session_name, state) → DecisionOutput | None` — Handle live LLM call with timeout, validation, and recording.
