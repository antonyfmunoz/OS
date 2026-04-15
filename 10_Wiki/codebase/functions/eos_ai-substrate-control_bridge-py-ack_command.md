---
type: codebase-function
file: eos_ai/substrate/control_bridge.py
line: 105
generated: 2026-04-12
---

# ack_command

**File:** [[eos_ai-substrate-control_bridge-py]] | **Line:** 105
**Signature:** `ack_command(command_id, result) → dict[str, Any]`

Mark a command as completed: removes from pending across nodes,
moves into a small bounded 'acked' ring per node.

## Calls

- [[eos_ai-substrate-control_bridge-py-_load_state]]
- [[eos_ai-substrate-control_bridge-py-_save_state]]
- [[eos_ai-substrate-storage-py-JSONFileStorage-get]]
- [[eos_ai-substrate-storage-py-NeonStorage-get]]
- [[eos_ai-substrate-storage-py-SubstrateStorage-get]]
