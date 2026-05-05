---
type: codebase-function
file: scripts/orchestrator.py
line: 361
generated: 2026-04-12
---

# ExecutionQueue.submit

**File:** [[scripts-orchestrator-py]] | **Line:** 361
**Signature:** `submit(job) → bool`

**Class:** [[scripts-orchestrator-py-ExecutionQueue]]

Enqueue a job run. Returns True if accepted, False otherwise.

Refuses if: queue full, already active with same concurrency key,
or job is DISABLED.

## Calls

- [[scripts-orchestrator-py-ActivityLog-emit]]
- [[scripts-orchestrator-py-Job-key]]

## Called By

- [[scripts-orchestrator-py-EventAgent-_dispatch_fs_event]]
- [[scripts-orchestrator-py-EventAgent-_on_workflow_complete]]
- [[scripts-orchestrator-py-ExecutionQueue-_dispatch_loop]]
- [[scripts-orchestrator-py-Orchestrator-submit]]
- [[scripts-orchestrator-py-Orchestrator-trigger]]
- [[scripts-orchestrator-py-SchedulerAgent-tick_once]]
