---
type: codebase-function
file: eos_ai/substrate/llm_planner.py
line: 529
generated: 2026-05-07
---

# build_llm_prompt

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 529
**Signature:** `build_llm_prompt(canonical_state, active_intents, registry, config) → str`

Build the LLM prompt from canonical state.

Deterministic: same inputs produce the same prompt string.
No randomness, no timestamps, no UUIDs.

## Calls

- [[eos_ai-substrate-llm_planner-py-_build_event_catalog]]
- [[eos_ai-substrate-llm_planner-py-_canonical_json]]
- [[eos_ai-substrate-llm_planner-py-_truncate_state]]

## Called By

- [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy-propose]]
