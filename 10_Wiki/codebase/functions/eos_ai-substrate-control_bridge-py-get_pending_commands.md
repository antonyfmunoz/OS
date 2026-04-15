---
type: codebase-function
file: eos_ai/substrate/control_bridge.py
line: 75
generated: 2026-04-12
---

# get_pending_commands

**File:** [[eos_ai-substrate-control_bridge-py]] | **Line:** 75
**Signature:** `get_pending_commands(node_id, limit) → list[cc.ControlCommand]`

Return pending commands for a node, in FIFO order. Never raises.

`limit` is an optional bound (Control Layer v2). When provided, the
returned list is truncated to at most `limit` envelopes. Hard cap is
enforced at 10 to keep batches bounded for the remote daemon.

## Calls

- [[eos_ai-substrate-control_bridge-py-_load_state]]
- [[eos_ai-substrate-storage-py-JSONFileStorage-get]]
- [[eos_ai-substrate-storage-py-NeonStorage-get]]
- [[eos_ai-substrate-storage-py-SubstrateStorage-get]]
