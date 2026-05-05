---
type: codebase-function
file: core/persistent_agents.py
line: 147
generated: 2026-04-12
---

# PersistentAgent.tick

**File:** [[core-persistent_agents-py]] | **Line:** 147
**Signature:** `tick() → TickResult`

**Class:** [[core-persistent_agents-py-PersistentAgent]]

Run one tick. Never raises.

## Calls

- [[core-persistent_agents-py-HealerAgent-tick_impl]]
- [[core-persistent_agents-py-LibrarianAgent-tick_impl]]
- [[core-persistent_agents-py-ObserverAgent-tick_impl]]
- [[core-persistent_agents-py-PersistentAgent-_save_state]]
- [[core-persistent_agents-py-PersistentAgent-tick_impl]]
- [[core-persistent_agents-py-_emit_agent_log]]

## Called By

- [[core-control_plane-py-ControlPlane-_tick_all]]
