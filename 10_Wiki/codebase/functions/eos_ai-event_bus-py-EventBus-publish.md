---
type: codebase-function
file: eos_ai/event_bus.py
line: 113
generated: 2026-04-12
---

# EventBus.publish

**File:** [[eos_ai-event_bus-py]] | **Line:** 113
**Signature:** `publish(event_type, payload) → list[Any]`

**Class:** [[eos_ai-event_bus-py-EventBus]]

Fire all handlers for this event type synchronously.
Persists the event to memory.db regardless of handler count.
Returns list of results from each handler.

## Calls

- [[eos_ai-event_bus-py-EventBus-_log_event]]

## Called By

- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-process_signal_queue]]
