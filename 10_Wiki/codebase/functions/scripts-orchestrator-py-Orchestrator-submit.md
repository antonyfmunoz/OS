---
type: codebase-function
file: scripts/orchestrator.py
line: 825
generated: 2026-04-12
---

# Orchestrator.submit

**File:** [[scripts-orchestrator-py]] | **Line:** 825
**Signature:** `submit(job) → bool`

**Class:** [[scripts-orchestrator-py-Orchestrator]]

*No docstring.*

## Calls

- [[scripts-orchestrator-py-ActivityLog-emit]]
- [[scripts-orchestrator-py-ExecutionQueue-submit]]
- [[scripts-orchestrator-py-Verifier-system_is_healthy]]

## Called By

- [[scripts-orchestrator-py-EventAgent-_dispatch_fs_event]]
- [[scripts-orchestrator-py-EventAgent-_on_workflow_complete]]
- [[scripts-orchestrator-py-ExecutionQueue-_dispatch_loop]]
- [[scripts-orchestrator-py-Orchestrator-trigger]]
- [[scripts-orchestrator-py-SchedulerAgent-tick_once]]
