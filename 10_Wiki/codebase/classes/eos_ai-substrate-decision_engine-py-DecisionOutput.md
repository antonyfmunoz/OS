---
type: codebase-class
file: eos_ai/substrate/decision_engine.py
line: 50
generated: 2026-05-07
---

# DecisionOutput

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 50

The result of a decision evaluation.

Fields:
    decision_id: Unique ID for tracing this decision.
    event_type: The event type to emit.
...

## Methods

- [[eos_ai-substrate-decision_engine-py-DecisionOutput-action_event]]`() → SchedulerEvent` — Build the SchedulerEvent for the chosen action.
- [[eos_ai-substrate-decision_engine-py-DecisionOutput-observability_event]]`() → SchedulerEvent` — Build the DECISION_MADE observability event.

## Decorators

- `@dataclass`
