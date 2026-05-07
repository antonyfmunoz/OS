---
type: codebase-class
file: eos_ai/substrate/llm_planner.py
line: 602
generated: 2026-05-07
---

# LLMPlanningStrategy

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 602

Constrained plan proposer.  Subordinate component.

Does NOT implement DecisionStrategy.  Owned by ReplayableStrategy.

Responsibilities:
...

## Methods

- [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy-__init__]]`(llm_fn, registry, config) → None` — 
- [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy-name]]`() → str` — 
- [[eos_ai-substrate-llm_planner-py-LLMPlanningStrategy-propose]]`(canonical_state, state_hash, active_intents) → LLMProposalResult` — Propose candidate events from current state.
