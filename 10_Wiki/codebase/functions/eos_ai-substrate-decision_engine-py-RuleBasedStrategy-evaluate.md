---
type: codebase-function
file: eos_ai/substrate/decision_engine.py
line: 170
generated: 2026-05-07
---

# RuleBasedStrategy.evaluate

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 170
**Signature:** `evaluate(state) → DecisionOutput | None`

**Class:** [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy]]

Evaluate rules in priority order. First match wins.

## Calls

- [[eos_ai-substrate-decision_engine-py-_compute_state_hash]]
- [[eos_ai-substrate-decision_engine-py-_log]]
- [[eos_ai-substrate-event_scheduler-py-_log]]

## Called By

- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate]]
- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate_snapshot]]
- [[eos_ai-substrate-decision_engine-py-evaluate_and_emit]]
- [[eos_ai-substrate-planner-py-IntentAwareStrategy-evaluate]]
