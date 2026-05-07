---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 442
generated: 2026-05-07
---

# resume_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 442
**Signature:** `resume_live_session(live_session_id) → LiveSession`

Transition session PAUSED -> ACTIVE.

Raises ValueError if session not found.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
