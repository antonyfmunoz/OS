---
type: codebase-class
file: eos_ai/event_bus.py
line: 59
generated: 2026-04-12
---

# EventBus

**File:** [[eos_ai-event_bus-py]] | **Line:** 59

Singleton event bus. Use EventBus() anywhere — always returns the same
instance. Thread-safe.

## Methods

- [[eos_ai-event_bus-py-EventBus-__new__]]`() → 'EventBus'` — 
- [[eos_ai-event_bus-py-EventBus-_log_event]]`(event_type, payload, handled_by) → str` — 
- [[eos_ai-event_bus-py-EventBus-subscribe]]`(event_type, handler_fn) → None` — Register a handler for an event type.
- [[eos_ai-event_bus-py-EventBus-publish]]`(event_type, payload) → list[Any]` — Fire all handlers for this event type synchronously.
- [[eos_ai-event_bus-py-EventBus-publish_async]]`(event_type, payload) → None` — Fire all handlers in a background daemon thread.
