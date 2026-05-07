---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 482
generated: 2026-05-07
---

# fail_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 482
**Signature:** `fail_live_session(live_session_id) → LiveSession`

Transition session to FAILED. Sets last_event with error info.

Raises ValueError if session not found.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
