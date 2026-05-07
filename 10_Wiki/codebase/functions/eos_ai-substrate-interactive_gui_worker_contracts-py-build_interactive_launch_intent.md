---
type: codebase-function
file: eos_ai/substrate/interactive_gui_worker_contracts.py
line: 55
generated: 2026-05-07
---

# build_interactive_launch_intent

**File:** [[eos_ai-substrate-interactive_gui_worker_contracts-py]] | **Line:** 55
**Signature:** `build_interactive_launch_intent(work_order_id, target_account) → dict[str, Any]`

Build the intent message that the VPS sends to the local worker.

The local interactive worker reads this and executes the Chrome launch
from its interactive desktop context.

## Calls

- [[eos_ai-substrate-interactive_gui_worker_contracts-py-build_interactive_chrome_launch_command]]
