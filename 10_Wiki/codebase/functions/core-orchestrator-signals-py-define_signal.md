---
type: codebase-function
file: core/orchestrator/signals.py
line: 96
generated: 2026-05-07
---

# define_signal

**File:** [[core-orchestrator-signals-py]] | **Line:** 96
**Signature:** `define_signal(name) → None`

Create the on-disk directories for a signal. Idempotent.

## Calls

- [[core-orchestrator-signals-py-_pending_dir]]
- [[core-orchestrator-signals-py-_processed_dir]]

## Called By

- [[core-orchestrator-signals-py-emit_signal]]
- [[core-orchestrator-signals-py-register_handler]]
