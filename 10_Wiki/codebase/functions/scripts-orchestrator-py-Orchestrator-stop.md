---
type: codebase-function
file: scripts/orchestrator.py
line: 854
generated: 2026-05-07
---

# Orchestrator.stop

**File:** [[scripts-orchestrator-py]] | **Line:** 854
**Signature:** `stop() → None`

**Class:** [[scripts-orchestrator-py-Orchestrator]]

*No docstring.*

## Calls

- [[scripts-orchestrator-py-ActivityLog-emit]]
- [[scripts-orchestrator-py-EventAgent-stop]]
- [[scripts-orchestrator-py-ExecutionQueue-stop]]
- [[scripts-orchestrator-py-SchedulerAgent-stop]]

## Called By

- [[core-control_plane-py-ControlPlane-loop_until_signal]]
- [[core-control_plane-py-ControlPlane-stop]]
- [[core-control_plane-py-_cmd_start]]
- [[scripts-orchestrator-py-EventAgent-stop]]
- [[scripts-orchestrator-py-Orchestrator-wait]]
- [[scripts-orchestrator-py-_cmd_start]]
- [[scripts-orchestrator-py-_cmd_trigger]]
- [[scripts-orchestrator-py-_install_signal_handlers]]
