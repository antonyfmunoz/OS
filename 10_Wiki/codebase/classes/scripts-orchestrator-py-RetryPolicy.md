---
type: codebase-class
file: scripts/orchestrator.py
line: 725
generated: 2026-04-12
---

# RetryPolicy

**File:** [[scripts-orchestrator-py]] | **Line:** 725

Exponential backoff across job runs.

Invoked via on_complete: after a failure, schedules the job for a retry
after base * 2^(consecutive_failures-1) seconds by setting next_run_at.
For EVENT jobs we don't reschedule — the next event will retry naturally.

## Methods

- [[scripts-orchestrator-py-RetryPolicy-__init__]]`(orchestrator) → None` — 
- [[scripts-orchestrator-py-RetryPolicy-_handle]]`(job, result) → None` — 
