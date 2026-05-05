---
type: codebase-function
file: eos_ai/substrate/session_watcher.py
line: 195
generated: 2026-04-12
---

# SessionWatcher.wait_for_reply

**File:** [[eos_ai-substrate-session_watcher-py]] | **Line:** 195
**Signature:** `wait_for_reply(timeout) → str`

**Class:** [[eos_ai-substrate-session_watcher-py-SessionWatcher]]

Block until the watcher detects a complete reply.

Thread-safe: clears prior state under the watcher lock so a
concurrent _run_loop iteration cannot set-then-lose the event.

## Called By

- [[eos_ai-substrate-session_watcher-py-ask_session_watched]]
