---
type: codebase-function
file: core/control_plane.py
line: 173
generated: 2026-05-07
---

# ControlPlane.loop_until_signal

**File:** [[core-control_plane-py]] | **Line:** 173
**Signature:** `loop_until_signal(save_every) → None`

**Class:** [[core-control_plane-py-ControlPlane]]

Block until stop() or SIGINT. Saves orchestrator state periodically.

## Calls

- [[core-control_plane-py-ControlPlane-stop]]
- [[scripts-orchestrator-py-EventAgent-stop]]
- [[scripts-orchestrator-py-ExecutionQueue-stop]]
- [[scripts-orchestrator-py-Orchestrator-save_state]]
- [[scripts-orchestrator-py-Orchestrator-stop]]
- [[scripts-orchestrator-py-SchedulerAgent-stop]]

## Called By

- [[core-control_plane-py-_cmd_start]]
