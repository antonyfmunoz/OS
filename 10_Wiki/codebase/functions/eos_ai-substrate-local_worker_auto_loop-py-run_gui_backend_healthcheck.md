---
type: codebase-function
file: eos_ai/substrate/local_worker_auto_loop.py
line: 499
generated: 2026-05-07
---

# run_gui_backend_healthcheck

**File:** [[eos_ai-substrate-local_worker_auto_loop-py]] | **Line:** 499
**Signature:** `run_gui_backend_healthcheck() → dict[str, str]`

Run GUI backend checks via safe subprocess import tests.

Returns dict of candidate → output string.
No mouse, keyboard, browser, or screen interaction.

## Called By

- [[eos_ai-substrate-local_worker_auto_loop-py-run_auto_loop]]
