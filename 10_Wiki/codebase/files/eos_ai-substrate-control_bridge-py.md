---
type: codebase-file
path: eos_ai/substrate/control_bridge.py
module: eos_ai.substrate.control_bridge
lines: 173
size: 5584
generated: 2026-04-11
---

# eos_ai/substrate/control_bridge.py

Control Layer v1 — Control Bridge (VPS side).

A bounded, file-backed queue of ControlCommand envelopes addressed to a node.
No networking. The bridge is a queue, not a transport. Local-first by design.

...

**Lines:** 173 | **Size:** 5,584 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-storage-py]]

## Contains

- **fn** [[eos_ai-substrate-control_bridge-py-_load_state]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-control_bridge-py-_save_state]]`(state) → None`
- **fn** [[eos_ai-substrate-control_bridge-py-send_command]]`(command) → dict[str, Any]`
- **fn** [[eos_ai-substrate-control_bridge-py-get_pending_commands]]`(node_id, limit) → list[cc.ControlCommand]`
- **fn** [[eos_ai-substrate-control_bridge-py-ack_command]]`(command_id, result) → dict[str, Any]`
- **fn** [[eos_ai-substrate-control_bridge-py-queue_depth]]`(node_id) → int`
- **fn** [[eos_ai-substrate-control_bridge-py-clear_queue]]`(node_id) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import threading
from typing import Any
from eos_ai.substrate import control_commands as cc
from eos_ai.substrate.storage import get_storage
```
