---
type: codebase-function
file: eos_ai/substrate/gui_backend_healthcheck.py
line: 96
generated: 2026-05-07
---

# generate_healthcheck_commands

**File:** [[eos_ai-substrate-gui_backend_healthcheck-py]] | **Line:** 96
**Signature:** `generate_healthcheck_commands() → list[BackendCheck]`

Generate safe healthcheck commands for the local worker.

These commands detect presence of GUI backends without performing
any mouse/keyboard/browser actions.

## Called By

- [[eos_ai-substrate-gui_backend_healthcheck-py-build_healthcheck_report_from_results]]
