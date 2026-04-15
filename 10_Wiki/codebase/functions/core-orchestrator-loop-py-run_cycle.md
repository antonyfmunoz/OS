---
type: codebase-function
file: core/orchestrator/loop.py
line: 396
generated: 2026-04-12
---

# run_cycle

**File:** [[core-orchestrator-loop-py]] | **Line:** 396
**Signature:** `run_cycle(orch, config) → CycleReport`

Run exactly one orchestrator cycle. Safe to call from cron.

## Calls

- [[core-orchestrator-loop-py-_drain_signals]]
- [[core-orchestrator-loop-py-_scan_failures]]
- [[core-orchestrator-loop-py-_scan_stale_deferred]]
- [[core-orchestrator-loop-py-_write_heartbeat]]

## Called By

- [[core-orchestrator-loop-py-run_forever]]
- [[scripts-orchestrator_loop-py-main]]
