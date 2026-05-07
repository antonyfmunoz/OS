---
type: codebase-function
file: eos_ai/substrate/node_transport.py
line: 227
generated: 2026-05-07
---

# send_task_via_http

**File:** [[eos_ai-substrate-node_transport-py]] | **Line:** 227
**Signature:** `send_task_via_http(action_dict) → Optional[dict]`

Send a SafeAction to the local daemon via HTTP and return the result.

Returns None on any transport failure. Callers should fall back to
file bus or VPS execution on None.

## Calls

- [[eos_ai-substrate-node_transport-py-_log]]
