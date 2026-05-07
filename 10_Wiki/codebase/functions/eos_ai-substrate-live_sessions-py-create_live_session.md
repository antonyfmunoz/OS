---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 373
generated: 2026-05-07
---

# create_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 373
**Signature:** `create_live_session(title, session_type) → LiveSession`

Create and persist a new live session.

If day_session_id is not provided, attempts to auto-attach from the
current OperatorSession.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSession-new]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_current_day_session_id]]
- [[eos_ai-substrate-live_sessions-py-_log]]
