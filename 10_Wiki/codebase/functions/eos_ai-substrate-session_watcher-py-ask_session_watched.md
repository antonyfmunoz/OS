---
type: codebase-function
file: eos_ai/substrate/session_watcher.py
line: 675
generated: 2026-05-07
---

# ask_session_watched

**File:** [[eos_ai-substrate-session_watcher-py]] | **Line:** 675
**Signature:** `ask_session_watched(target, session_name, text) → dict[str, Any]`

Send a message and wait for the watcher to detect the reply.

If no watcher is running for this session, returns fallback signal
so the caller can use the original ask_session polling.

...

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-send_message]]
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-wait_for_reply]]
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-wait_until_idle]]
- [[eos_ai-substrate-session_watcher-py-get_watcher]]
