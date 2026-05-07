---
type: codebase-function
file: eos_ai/substrate/event_scheduler.py
line: 193
generated: 2026-05-07
---

# EventScheduler.subscribe

**File:** [[eos_ai-substrate-event_scheduler-py]] | **Line:** 193
**Signature:** `subscribe(event_type, handler, guard, name) → None`

**Class:** [[eos_ai-substrate-event_scheduler-py-EventScheduler]]

Register a handler for an event type with optional guard.

Multiple handlers can subscribe to the same event type.
Guards are evaluated before handler execution.

## Calls

- [[eos_ai-substrate-event_scheduler-py-_log]]
