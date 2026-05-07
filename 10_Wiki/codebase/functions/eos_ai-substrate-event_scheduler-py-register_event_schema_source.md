---
type: codebase-function
file: eos_ai/substrate/event_scheduler.py
line: 51
generated: 2026-05-07
---

# register_event_schema_source

**File:** [[eos_ai-substrate-event_scheduler-py]] | **Line:** 51
**Signature:** `register_event_schema_source(registry) → None`

Register an EventTypeRegistry for runtime mutation enforcement.

The scheduler uses this registry to look up EventSchema.is_mutation
for each event type.  When is_mutation=False and a handler returns
mutations, NonMutatingEventViolation is raised.
...
