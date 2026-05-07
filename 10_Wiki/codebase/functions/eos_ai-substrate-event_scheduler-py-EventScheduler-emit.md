---
type: codebase-function
file: eos_ai/substrate/event_scheduler.py
line: 188
generated: 2026-05-07
---

# EventScheduler.emit

**File:** [[eos_ai-substrate-event_scheduler-py]] | **Line:** 188
**Signature:** `emit(event) → None`

**Class:** [[eos_ai-substrate-event_scheduler-py-EventScheduler]]

Enqueue an event for processing. Returns immediately.

## Called By

- [[eos_ai-substrate-decision_engine-py-evaluate_and_emit]]
- [[eos_ai-substrate-event_scheduler-py-EventScheduler-_route]]
- [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_check_drift]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_emit_proposed_events]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-_handle_cache_miss]]
- [[eos_ai-substrate-llm_replay-py-ReplayableStrategy-evaluate]]
