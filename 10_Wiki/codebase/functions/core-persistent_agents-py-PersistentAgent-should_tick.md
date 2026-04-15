---
type: codebase-function
file: core/persistent_agents.py
line: 131
generated: 2026-04-12
---

# PersistentAgent.should_tick

**File:** [[core-persistent_agents-py]] | **Line:** 131
**Signature:** `should_tick(now) → bool`

**Class:** [[core-persistent_agents-py-PersistentAgent]]

True if at least interval_sec has elapsed since last_tick_at.

## Called By

- [[core-control_plane-py-ControlPlane-_tick_all]]
