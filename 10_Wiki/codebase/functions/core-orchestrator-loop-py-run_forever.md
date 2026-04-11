---
type: codebase-function
file: core/orchestrator/loop.py
line: 425
generated: 2026-04-11
---

# run_forever

**File:** [[core-orchestrator-loop-py]] | **Line:** 425
**Signature:** `run_forever(orch, config, max_cycles) → None`

Dev-mode convenience runner. Prefer cron/systemd in production.

Stops after `max_cycles` if provided — useful for smoke tests.

## Calls

- [[core-orchestrator-loop-py-CycleReport-to_dict]]
- [[core-orchestrator-loop-py-run_cycle]]

## Called By

- [[scripts-orchestrator_loop-py-main]]
