---
type: codebase-function
file: eos_ai/substrate/event_scheduler.py
line: 212
generated: 2026-05-07
---

# EventScheduler.run

**File:** [[eos_ai-substrate-event_scheduler-py]] | **Line:** 212
**Signature:** `run() → RunResult`

**Class:** [[eos_ai-substrate-event_scheduler-py-EventScheduler]]

Drain the event queue. Process events breadth-first.

Each event is routed to its subscribers. Follow-up events from
handlers go to the back of the queue. Dedup prevents double-
processing. Circuit breaker at max_iterations prevents infinite loops.

## Calls

- [[eos_ai-substrate-event_scheduler-py-EventScheduler-_route]]
- [[eos_ai-substrate-event_scheduler-py-_log]]

## Called By

- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
