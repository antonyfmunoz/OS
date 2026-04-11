---
type: codebase-function
file: eos_ai/substrate/session_control.py
line: 204
generated: 2026-04-11
---

# maybe_auto_clear

**File:** [[eos_ai-substrate-session_control-py]] | **Line:** 204
**Signature:** `maybe_auto_clear(session_name) → dict[str, Any]`

Increment the message counter and clear if threshold is reached.

Called inside the request flow — no background threads. Returns a dict
indicating whether a clear was triggered.

## Calls

- [[eos_ai-substrate-session_control-py-_auto_clear_threshold]]
- [[eos_ai-substrate-session_control-py-_increment_count]]
- [[eos_ai-substrate-session_control-py-_log]]
- [[eos_ai-substrate-session_control-py-_reset_count]]
- [[eos_ai-substrate-session_control-py-clear_session]]
