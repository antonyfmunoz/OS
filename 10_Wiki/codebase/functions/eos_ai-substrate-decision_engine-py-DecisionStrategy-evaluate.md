---
type: codebase-function
file: eos_ai/substrate/decision_engine.py
line: 113
generated: 2026-05-07
---

# DecisionStrategy.evaluate

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 113
**Signature:** `evaluate(state) → DecisionOutput | None`

**Class:** [[eos_ai-substrate-decision_engine-py-DecisionStrategy]]

Evaluate the current state and return a decision, or None.

MUST be deterministic: same state dict → same DecisionOutput.
MUST NOT have side effects.

## Called By

- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate]]
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate_snapshot]]
- [[eos_ai-substrate-decision_engine-py-evaluate_and_emit]]
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-evaluate]]
