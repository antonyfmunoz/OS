---
type: codebase-class
file: eos_ai/substrate/event_scheduler.py
line: 42
generated: 2026-05-07
---

# NonMutatingEventViolation

**File:** [[eos_ai-substrate-event_scheduler-py]] | **Line:** 42

Raised when a handler for a non-mutating event returns mutations.

Non-mutating events (EventSchema.is_mutation=False) are observability-
only.  Their handlers must never return state mutations.  This is
enforced structurally at the scheduler execution boundary.

## Inherits From

- `RuntimeError`
