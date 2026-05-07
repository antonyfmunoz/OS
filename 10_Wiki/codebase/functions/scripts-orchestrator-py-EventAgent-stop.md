---
type: codebase-function
file: scripts/orchestrator.py
line: 651
generated: 2026-05-07
---

# EventAgent.stop

**File:** [[scripts-orchestrator-py]] | **Line:** 651
**Signature:** `stop(timeout) → None`

**Class:** [[scripts-orchestrator-py-EventAgent]]

*No docstring.*

## Calls

- [[scripts-orchestrator-py-ExecutionQueue-stop]]
- [[scripts-orchestrator-py-Orchestrator-stop]]
- [[scripts-orchestrator-py-SchedulerAgent-stop]]

## Called By

- [[core-control_plane-py-ControlPlane-loop_until_signal]]
- [[core-control_plane-py-ControlPlane-stop]]
- [[core-control_plane-py-_cmd_start]]
- [[scripts-orchestrator-py-Orchestrator-stop]]
- [[scripts-orchestrator-py-Orchestrator-wait]]
- [[scripts-orchestrator-py-_cmd_start]]
- [[scripts-orchestrator-py-_cmd_trigger]]
- [[scripts-orchestrator-py-_install_signal_handlers]]
