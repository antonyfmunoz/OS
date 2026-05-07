---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 551
generated: 2026-05-07
---

# detach_pipeline_from_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 551
**Signature:** `detach_pipeline_from_live_session(live_session_id, pipeline_id) → LiveSession`

Detach a pipeline from a live session.

Raises ValueError if session not found.
No error if pipeline_id not attached (idempotent).

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
