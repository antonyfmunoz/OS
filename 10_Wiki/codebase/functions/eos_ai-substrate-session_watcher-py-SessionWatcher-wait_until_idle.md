---
type: codebase-function
file: eos_ai/substrate/session_watcher.py
line: 248
generated: 2026-05-07
---

# SessionWatcher.wait_until_idle

**File:** [[eos_ai-substrate-session_watcher-py]] | **Line:** 248
**Signature:** `wait_until_idle(timeout, min_stable_polls) → bool`

**Class:** [[eos_ai-substrate-session_watcher-py-SessionWatcher]]

Block until the session is truly idle (prompt visible, no streaming,
output stable for *min_stable_polls* consecutive polls).

Returns True if idle was confirmed, False if timed out.

## Called By

- [[eos_ai-substrate-session_watcher-py-ask_session_watched]]
