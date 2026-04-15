---
type: codebase-class
file: core/persistent_agents.py
line: 337
generated: 2026-04-12
---

# HealerAgent

**File:** [[core-persistent_agents-py]] | **Line:** 337

Reacts to Observer alerts and stuck state.

Conservative by design. Actions taken:
  1. If Observer reports disabled orchestrator jobs AND the job's last
     failure was >6h ago, emit a `job_reenable_requested` signal into
...

## Inherits From

- [[core-persistent_agents-py-PersistentAgent]]

## Methods

- [[core-persistent_agents-py-HealerAgent-tick_impl]]`(state) → TickResult` — 
