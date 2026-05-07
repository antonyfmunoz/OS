---
type: codebase-function
file: eos_ai/substrate/local_control.py
line: 450
generated: 2026-05-07
---

# execute_control_request

**File:** [[eos_ai-substrate-local_control-py]] | **Line:** 450
**Signature:** `execute_control_request(request_id) → LocalControlRequest`

Mark a request as executing and dispatch to the appropriate handler.

Routes browser actions through browser_agent and OS-level actions
through subprocess calls. Scene actions resolve steps and execute
each one recursively.

## Calls

- [[eos_ai-substrate-local_control-py-LocalControlStore-default]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-get]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-put]]
- [[eos_ai-substrate-local_control-py-_log]]
- [[eos_ai-substrate-local_control-py-_utcnow]]

## Called By

- [[eos_ai-substrate-local_control-py-_dispatch_open_scene]]
