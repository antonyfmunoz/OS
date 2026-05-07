---
type: codebase-function
file: eos_ai/substrate/local_control.py
line: 400
generated: 2026-05-07
---

# submit_control_request

**File:** [[eos_ai-substrate-local_control-py]] | **Line:** 400
**Signature:** `submit_control_request(action, payload) → LocalControlRequest`

Submit a local control request.

1. Check mode enforcement — if action not allowed, set status=BLOCKED.
2. Check local_available — if False, set status=BLOCKED with error.
3. If allowed, set status=PENDING (actual execution is external).
...

## Calls

- [[eos_ai-substrate-local_control-py-LocalControlRequest-new]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-default]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-get_mode]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-put]]
- [[eos_ai-substrate-local_control-py-_log]]
- [[eos_ai-substrate-local_control-py-_utcnow]]
- [[eos_ai-substrate-local_control-py-is_action_allowed]]

## Called By

- [[eos_ai-substrate-local_control-py-open_scene]]
