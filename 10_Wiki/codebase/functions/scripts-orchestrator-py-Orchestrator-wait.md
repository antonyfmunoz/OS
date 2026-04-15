---
type: codebase-function
file: scripts/orchestrator.py
line: 864
generated: 2026-04-12
---

# Orchestrator.wait

**File:** [[scripts-orchestrator-py]] | **Line:** 864
**Signature:** `wait() → None`

**Class:** [[scripts-orchestrator-py-Orchestrator]]

Block until stop() is called. Intended for foreground `start`.

## Calls

- [[scripts-orchestrator-py-EventAgent-stop]]
- [[scripts-orchestrator-py-ExecutionQueue-stop]]
- [[scripts-orchestrator-py-Orchestrator-stop]]
- [[scripts-orchestrator-py-SchedulerAgent-stop]]

## Called By

- [[core-control_plane-py-ControlPlane-_agent_loop]]
- [[scripts-orchestrator-py-SchedulerAgent-_loop]]
