---
type: codebase-class
file: scripts/orchestrator.py
line: 493
generated: 2026-04-12
---

# SchedulerAgent

**File:** [[scripts-orchestrator-py]] | **Line:** 493

Time-based trigger thread. Ticks once a second.

For interval jobs: schedules next_run = now + interval_sec after each
submission (drift-free — we don't care about wall-clock precision, only
monotonic cadence).
...

## Methods

- [[scripts-orchestrator-py-SchedulerAgent-__init__]]`(orchestrator) → None` — 
- [[scripts-orchestrator-py-SchedulerAgent-start]]`() → None` — 
- [[scripts-orchestrator-py-SchedulerAgent-stop]]`(timeout) → None` — 
- [[scripts-orchestrator-py-SchedulerAgent-tick_once]]`() → int` — One pass over the registry. Returns the number of jobs submitted.
- [[scripts-orchestrator-py-SchedulerAgent-_loop]]`() → None` — 
