---
type: codebase-function
file: eos_ai/substrate/decision_engine.py
line: 294
generated: 2026-05-07
---

# evaluate_and_emit

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 294
**Signature:** `evaluate_and_emit(engine, store, scheduler) → DecisionOutput | None`

Convenience: evaluate + emit both events into the scheduler.

Returns the DecisionOutput if a decision was made, None otherwise.
This is the standard integration point for the post-drain hook.

## Calls

- [[eos_ai-substrate-decision_engine-py-DecisionEngine-evaluate]]
- [[eos_ai-substrate-decision_engine-py-DecisionStrategy-evaluate]]
- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-evaluate]]
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-emit]]
