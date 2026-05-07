---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 401
generated: 2026-05-07
---

# start_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 401
**Signature:** `start_live_session(live_session_id) → LiveSession`

Transition session CREATED -> ACTIVE.

Raises ValueError if session not found.
Logs warning if not in CREATED state (but still transitions for recovery).

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
