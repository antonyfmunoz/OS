---
type: codebase-function
file: eos_ai/substrate/planner.py
line: 368
generated: 2026-05-07
---

# IntentAwareStrategy.evaluate

**File:** [[eos_ai-substrate-planner-py]] | **Line:** 368
**Signature:** `evaluate(state) → DecisionOutput | None`

**Class:** [[eos_ai-substrate-planner-py-IntentAwareStrategy]]

Try LLM planner first, then deterministic planner, then rules.

## Calls

- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate]]
- [[eos_ai-substrate-decision_engine-py-DecisionStrategy-evaluate]]
- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-evaluate]]
- [[eos_ai-substrate-planner-py-PlannerStrategy-evaluate]]
