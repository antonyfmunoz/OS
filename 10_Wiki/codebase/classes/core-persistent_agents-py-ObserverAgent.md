---
type: codebase-class
file: core/persistent_agents.py
line: 210
generated: 2026-04-12
---

# ObserverAgent

**File:** [[core-persistent_agents-py]] | **Line:** 210

Reads logs, computes health, emits alerts into state.

Alerts are stored in `state["custom"]["alerts"]` so the Healer can react
on its next tick. Observer never calls LLMs or mutates anything.

...

## Inherits From

- [[core-persistent_agents-py-PersistentAgent]]

## Methods

- [[core-persistent_agents-py-ObserverAgent-tick_impl]]`(state) → TickResult` — 
- [[core-persistent_agents-py-ObserverAgent-_get_advisor_interpretation]]`(alerts) → str | None` — Ask the advisor to interpret system alerts. Non-fatal.
