---
type: codebase-class
file: core/persistent_agents.py
line: 421
generated: 2026-04-12
---

# LibrarianAgent

**File:** [[core-persistent_agents-py]] | **Line:** 421

Consolidates recent workflow runs into short notes and remembers them.

One note per tick, max. The LLM call is dispatched via the harness so
it obeys the capability profile + router fallback chain.

...

## Inherits From

- [[core-persistent_agents-py-PersistentAgent]]

## Methods

- [[core-persistent_agents-py-LibrarianAgent-tick_impl]]`(state) → TickResult` — 
