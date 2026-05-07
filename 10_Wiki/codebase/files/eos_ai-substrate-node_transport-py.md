---
type: codebase-file
path: eos_ai/substrate/node_transport.py
module: eos_ai.substrate.node_transport
lines: 291
size: 10379
generated: 2026-05-07
---

# eos_ai/substrate/node_transport.py

NodeTransport — aiohttp transport adapter for local station daemon.

Thin HTTP server that exposes the station daemon's capabilities over
the network. This is an ADDITIVE transport alongside the existing
file bus — it does NOT replace file bus polling.
...

**Lines:** 291 | **Size:** 10,379 bytes

## Contains

- **class** [[eos_ai-substrate-node_transport-py-NodeTransportServer]] — 8 methods
- **fn** [[eos_ai-substrate-node_transport-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-node_transport-py-send_task_via_http]]`(action_dict) → Optional[dict]`
- **fn** [[eos_ai-substrate-node_transport-py-check_http_health]]`() → bool`

## Import Statements

```python
from __future__ import annotations
import sys
from typing import TYPE_CHECKING
from typing import Any
from typing import Optional
```
