---
type: codebase-function
file: eos_ai/substrate/interactive_gui_worker_contracts.py
line: 39
generated: 2026-05-07
---

# build_interactive_chrome_launch_command

**File:** [[eos_ai-substrate-interactive_gui_worker_contracts-py]] | **Line:** 39
**Signature:** `build_interactive_chrome_launch_command(url, chrome_path) → str`

Build the PowerShell command for interactive Chrome launch.

This command must be run from an interactive Windows session,
NOT via SSH from the VPS.

## Called By

- [[eos_ai-substrate-interactive_gui_worker_contracts-py-build_interactive_launch_intent]]
