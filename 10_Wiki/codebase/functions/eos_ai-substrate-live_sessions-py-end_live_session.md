---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 462
generated: 2026-05-07
---

# end_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 462
**Signature:** `end_live_session(live_session_id) → LiveSession`

Transition session to ENDED. Sets summary if provided.

Raises ValueError if session not found.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
