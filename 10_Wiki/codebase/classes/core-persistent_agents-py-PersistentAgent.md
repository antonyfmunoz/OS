---
type: codebase-class
file: core/persistent_agents.py
line: 77
generated: 2026-04-12
---

# PersistentAgent

**File:** [[core-persistent_agents-py]] | **Line:** 77

Base class for long-running agents.

Subclasses override `tick_impl(state) → TickResult` and declare:
  - name:        unique agent name (also the capability profile name)
  - interval_sec: minimum seconds between ticks

## Inherits From

- `ABC`

## Inherited By

- [[core-persistent_agents-py-ObserverAgent]]
- [[core-persistent_agents-py-HealerAgent]]
- [[core-persistent_agents-py-LibrarianAgent]]

## Methods

- [[core-persistent_agents-py-PersistentAgent-__init__]]`() → None` — 
- [[core-persistent_agents-py-PersistentAgent-_load_state]]`() → dict[str, Any]` — 
- [[core-persistent_agents-py-PersistentAgent-_save_state]]`() → None` — 
- [[core-persistent_agents-py-PersistentAgent-state]]`() → dict[str, Any]` — 
- [[core-persistent_agents-py-PersistentAgent-should_tick]]`(now) → bool` — True if at least interval_sec has elapsed since last_tick_at.
- [[core-persistent_agents-py-PersistentAgent-tick]]`() → TickResult` — Run one tick. Never raises.
- [[core-persistent_agents-py-PersistentAgent-tick_impl]]`(state) → TickResult` — Subclass hook. Return a TickResult. Update state["custom"] freely.
