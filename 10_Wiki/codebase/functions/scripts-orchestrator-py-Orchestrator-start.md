---
type: codebase-function
file: scripts/orchestrator.py
line: 840
generated: 2026-04-12
---

# Orchestrator.start

**File:** [[scripts-orchestrator-py]] | **Line:** 840
**Signature:** `start() → None`

**Class:** [[scripts-orchestrator-py-Orchestrator]]

*No docstring.*

## Calls

- [[scripts-orchestrator-py-ActivityLog-emit]]
- [[scripts-orchestrator-py-EventAgent-start]]
- [[scripts-orchestrator-py-ExecutionQueue-start]]
- [[scripts-orchestrator-py-SchedulerAgent-start]]

## Called By

- [[core-control_plane-py-ControlPlane-start]]
- [[core-control_plane-py-_cmd_start]]
- [[scripts-orchestrator-py-EventAgent-start]]
- [[scripts-orchestrator-py-ExecutionQueue-start]]
- [[scripts-orchestrator-py-SchedulerAgent-start]]
- [[scripts-orchestrator-py-_cmd_start]]
- [[scripts-orchestrator-py-_cmd_trigger]]
