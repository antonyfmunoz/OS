---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 422
generated: 2026-05-07
---

# pause_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 422
**Signature:** `pause_live_session(live_session_id) → LiveSession`

Transition session ACTIVE -> PAUSED.

Raises ValueError if session not found.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
