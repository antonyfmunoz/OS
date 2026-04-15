---
type: codebase-function
file: eos_ai/event_bus.py
line: 144
generated: 2026-04-12
---

# EventBus.publish_async

**File:** [[eos_ai-event_bus-py]] | **Line:** 144
**Signature:** `publish_async(event_type, payload) → None`

**Class:** [[eos_ai-event_bus-py-EventBus]]

Fire all handlers in a background daemon thread.
Returns immediately — caller is never blocked.

## Called By

- [[eos_ai-coordination_engine-py-CoordinationEngine-assign_task]]
