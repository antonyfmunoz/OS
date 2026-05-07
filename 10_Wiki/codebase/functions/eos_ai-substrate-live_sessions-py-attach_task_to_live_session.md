---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 503
generated: 2026-05-07
---

# attach_task_to_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 503
**Signature:** `attach_task_to_live_session(live_session_id, task_id) → LiveSession`

Attach a task to a live session. Deduplicates.

Raises ValueError if session not found.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
