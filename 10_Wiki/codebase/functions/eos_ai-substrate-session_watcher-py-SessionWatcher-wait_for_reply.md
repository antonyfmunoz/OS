---
type: codebase-function
file: eos_ai/substrate/session_watcher.py
line: 282
generated: 2026-05-07
---

# SessionWatcher.wait_for_reply

**File:** [[eos_ai-substrate-session_watcher-py]] | **Line:** 282
**Signature:** `wait_for_reply(timeout) → str`

**Class:** [[eos_ai-substrate-session_watcher-py-SessionWatcher]]

Block until the watcher detects a complete reply.

Adaptive timeout: if CC is actively working (WORKING state),
waits up to `timeout` seconds. If CC appears idle with no
output changes, gives up after _IDLE_TIMEOUT_S of inactivity.
...

## Called By

- [[eos_ai-substrate-session_watcher-py-ask_session_watched]]
