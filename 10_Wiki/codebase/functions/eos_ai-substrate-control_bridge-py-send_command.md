---
type: codebase-function
file: eos_ai/substrate/control_bridge.py
line: 50
generated: 2026-04-11
---

# send_command

**File:** [[eos_ai-substrate-control_bridge-py]] | **Line:** 50
**Signature:** `send_command(command) → dict[str, Any]`

Enqueue a command for the target node. Bounded and validated.
Returns {"ok": bool, "reason": str, "command_id": str|None}.

## Calls

- [[eos_ai-substrate-actions-py-SafeAction-to_dict]]
- [[eos_ai-substrate-control_bridge-py-_load_state]]
- [[eos_ai-substrate-control_bridge-py-_save_state]]
