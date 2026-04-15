---
type: codebase-function
file: core/control_plane.py
line: 156
generated: 2026-04-12
---

# ControlPlane.stop

**File:** [[core-control_plane-py]] | **Line:** 156
**Signature:** `stop() → None`

**Class:** [[core-control_plane-py-ControlPlane]]

*No docstring.*

## Calls

- [[core-control_plane-py-_log]]
- [[scripts-orchestrator-py-EventAgent-stop]]
- [[scripts-orchestrator-py-ExecutionQueue-stop]]
- [[scripts-orchestrator-py-Orchestrator-stop]]
- [[scripts-orchestrator-py-SchedulerAgent-stop]]

## Called By

- [[core-control_plane-py-ControlPlane-loop_until_signal]]
- [[core-control_plane-py-_cmd_start]]
