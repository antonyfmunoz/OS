---
type: codebase-function
file: scripts/orchestrator.py
line: 347
generated: 2026-04-12
---

# ExecutionQueue.stop

**File:** [[scripts-orchestrator-py]] | **Line:** 347
**Signature:** `stop() → None`

**Class:** [[scripts-orchestrator-py-ExecutionQueue]]

*No docstring.*

## Calls

- [[scripts-orchestrator-py-ActivityLog-emit]]

## Called By

- [[core-control_plane-py-ControlPlane-loop_until_signal]]
- [[core-control_plane-py-ControlPlane-stop]]
- [[core-control_plane-py-_cmd_start]]
- [[scripts-orchestrator-py-EventAgent-stop]]
- [[scripts-orchestrator-py-Orchestrator-stop]]
- [[scripts-orchestrator-py-Orchestrator-wait]]
- [[scripts-orchestrator-py-_cmd_start]]
- [[scripts-orchestrator-py-_cmd_trigger]]
- [[scripts-orchestrator-py-_install_signal_handlers]]
