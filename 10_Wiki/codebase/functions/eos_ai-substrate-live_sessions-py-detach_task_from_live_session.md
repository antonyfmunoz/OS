---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 535
generated: 2026-05-07
---

# detach_task_from_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 535
**Signature:** `detach_task_from_live_session(live_session_id, task_id) → LiveSession`

Detach a task from a live session.

Raises ValueError if session not found.
No error if task_id not attached (idempotent).

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
