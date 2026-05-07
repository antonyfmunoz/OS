---
type: codebase-class
file: core/control_plane.py
line: 89
generated: 2026-05-07
---

# ControlPlane

**File:** [[core-control_plane-py]] | **Line:** 89

Wraps Orchestrator + PersistentAgents behind one lifecycle.

## Methods

- [[core-control_plane-py-ControlPlane-__init__]]`() → None` — 
- [[core-control_plane-py-ControlPlane-register_agent]]`(agent) → None` — 
- [[core-control_plane-py-ControlPlane-register_job]]`(job) → None` — 
- [[core-control_plane-py-ControlPlane-agents]]`() → list[PersistentAgent]` — 
- [[core-control_plane-py-ControlPlane-start]]`() → None` — 
- [[core-control_plane-py-ControlPlane-stop]]`() → None` — 
- [[core-control_plane-py-ControlPlane-loop_until_signal]]`(save_every) → None` — Block until stop() or SIGINT. Saves orchestrator state periodically.
- [[core-control_plane-py-ControlPlane-_agent_loop]]`() → None` — Tick each persistent agent whenever its interval elapses.
- [[core-control_plane-py-ControlPlane-_tick_all]]`() → None` — 
- [[core-control_plane-py-ControlPlane-status]]`() → dict[str, Any]` — 
