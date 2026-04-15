---
type: codebase-function
file: scripts/orchestrator_status.py
line: 205
generated: 2026-04-12
---

# loop_heartbeat

**File:** [[scripts-orchestrator_status-py]] | **Line:** 205
**Signature:** `loop_heartbeat() → dict[str, Any]`

Read the orchestrator heartbeat written by core.orchestrator.loop.

Returns a dict with `present`, `alive`, `age_seconds`, plus the
raw heartbeat payload if it exists. `alive` is True when the
heartbeat was updated inside LOOP_STALE_THRESHOLD_S.

## Calls

- [[scripts-orchestrator_status-py-_age_seconds]]

## Called By

- [[scripts-orchestrator_status-py-build_snapshot]]
