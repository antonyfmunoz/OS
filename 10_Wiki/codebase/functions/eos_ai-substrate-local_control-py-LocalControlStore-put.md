---
type: codebase-function
file: eos_ai/substrate/local_control.py
line: 298
generated: 2026-05-07
---

# LocalControlStore.put

**File:** [[eos_ai-substrate-local_control-py]] | **Line:** 298
**Signature:** `put(request) → None`

**Class:** [[eos_ai-substrate-local_control-py-LocalControlStore]]

Persist a request (insert or update), pruning if over cap.

## Calls

- [[eos_ai-substrate-local_control-py-LocalControlStore-_flush]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-_prune]]

## Called By

- [[eos_ai-substrate-local_control-py-LocalControlStore-_flush]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-_flush_mode]]
- [[eos_ai-substrate-local_control-py-_dispatch_open_scene]]
- [[eos_ai-substrate-local_control-py-execute_control_request]]
- [[eos_ai-substrate-local_control-py-open_scene]]
- [[eos_ai-substrate-local_control-py-submit_control_request]]
