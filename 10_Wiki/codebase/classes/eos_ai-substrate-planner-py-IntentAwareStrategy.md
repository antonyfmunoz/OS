---
type: codebase-class
file: eos_ai/substrate/planner.py
line: 327
generated: 2026-05-07
---

# IntentAwareStrategy

**File:** [[eos_ai-substrate-planner-py]] | **Line:** 327

Composite strategy: LLM planner → deterministic planner → rules.

Priority chain:
1. LLM replayable strategy (if present and enabled).
2. Deterministic PlannerStrategy (intent-driven).
...

## Methods

- [[eos_ai-substrate-planner-py-IntentAwareStrategy-__init__]]`(planner, fallback, llm_planner) → None` — 
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-name]]`() → str` — 
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-planner]]`() → PlannerStrategy` — 
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-fallback]]`() → Any` — 
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-llm_planner]]`() → Any` — The LLM planning layer (ReplayableStrategy), or None.
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-evaluate]]`(state) → DecisionOutput | None` — Try LLM planner first, then deterministic planner, then rules.
