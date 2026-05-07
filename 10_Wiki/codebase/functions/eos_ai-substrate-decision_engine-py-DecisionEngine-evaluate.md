---
type: codebase-function
file: eos_ai/substrate/decision_engine.py
line: 240
generated: 2026-05-07
---

# DecisionEngine.evaluate

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 240
**Signature:** `evaluate(store) → DecisionOutput | None`

**Class:** [[eos_ai-substrate-decision_engine-py-DecisionEngine]]

Evaluate the current state and return a decision.

Takes a RuntimeStateStore and reads a snapshot (read-only).
Returns None if the engine is disabled or no decision applies.

## Calls

- [[eos_ai-substrate-decision_engine-py-DecisionStrategy-evaluate]]
- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-evaluate]]
- [[eos_ai-substrate-decision_engine-py-_log]]
- [[eos_ai-substrate-event_scheduler-py-_log]]

## Called By

- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate_snapshot]]
- [[eos_ai-substrate-decision_engine-py-evaluate_and_emit]]
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-evaluate]]
