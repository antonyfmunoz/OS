---
type: codebase-class
file: eos_ai/substrate/decision_engine.py
line: 200
generated: 2026-05-07
---

# DecisionEngine

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 200

Control-plane decision engine.

Reads state (read-only), delegates to a strategy, and returns
a DecisionOutput. Never modifies state or executes anything.

...

## Methods

- [[eos_ai-substrate-decision_engine-py-DecisionEngine-__init__]]`(strategy, enabled) → None` — 
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-strategy_name]]`() → str` — 
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-enabled]]`(value) → None` — 
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-enabled]]`(value) → None` — 
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluation_count]]`() → int` — 
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate]]`(store) → DecisionOutput | None` — Evaluate the current state and return a decision.
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate_snapshot]]`(snapshot) → DecisionOutput | None` — Evaluate a raw state dict directly.
