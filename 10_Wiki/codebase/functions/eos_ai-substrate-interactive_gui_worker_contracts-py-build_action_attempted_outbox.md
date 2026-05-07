---
type: codebase-function
file: eos_ai/substrate/interactive_gui_worker_contracts.py
line: 93
generated: 2026-05-07
---

# build_action_attempted_outbox

**File:** [[eos_ai-substrate-interactive_gui_worker_contracts-py]] | **Line:** 93
**Signature:** `build_action_attempted_outbox(work_order_id, command_exit_code, launch_context, chrome_path) → dict[str, Any]`

Build the ACTION_ATTEMPTED outbox message.

Written by the interactive worker AFTER running the command.
Does NOT claim visible success — waits for founder confirmation.
