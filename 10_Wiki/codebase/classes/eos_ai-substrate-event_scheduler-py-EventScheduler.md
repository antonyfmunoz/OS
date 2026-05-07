---
type: codebase-class
file: eos_ai/substrate/event_scheduler.py
line: 163
generated: 2026-05-07
---

# EventScheduler

**File:** [[eos_ai-substrate-event_scheduler-py]] | **Line:** 163

Event-driven scheduler with FIFO queue, guards, and dedup.

Usage:
    scheduler = EventScheduler(store, event_log)
    scheduler.subscribe("finalization_succeeded", handler, guard=my_guard)
...

## Methods

- [[eos_ai-substrate-event_scheduler-py-EventScheduler-__init__]]`(store, event_log) → None` — 
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-emit]]`(event) → None` — Enqueue an event for processing. Returns immediately.
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-subscribe]]`(event_type, handler, guard, name) → None` — Register a handler for an event type with optional guard.
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-run]]`() → RunResult` — Drain the event queue. Process events breadth-first.
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-reset]]`() → None` — Clear queue, dedup set, and subscribers. For testing.
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-pending_count]]`() → int` — Return number of events in the queue.
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-_route]]`(event) → RouteResult` — Route an event to all matching subscribers.
