---
type: codebase-function
file: eos_ai/event_bus.py
line: 99
generated: 2026-04-12
---

# EventBus.subscribe

**File:** [[eos_ai-event_bus-py]] | **Line:** 99
**Signature:** `subscribe(event_type, handler_fn) → None`

**Class:** [[eos_ai-event_bus-py-EventBus]]

Register a handler for an event type.
Multiple handlers per event type are supported — all will fire in
registration order.

## Called By

- [[eos_ai-event_bus-py-EventRegistry-register_defaults]]
- [[scripts-substrate_drainer_smoke_test-py-main]]
