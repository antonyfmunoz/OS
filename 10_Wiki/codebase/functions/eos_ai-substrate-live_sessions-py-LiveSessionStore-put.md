---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 288
generated: 2026-05-07
---

# LiveSessionStore.put

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 288
**Signature:** `put(session) → None`

**Class:** [[eos_ai-substrate-live_sessions-py-LiveSessionStore]]

Insert or update a session. Prunes if needed, then flushes to storage.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-_flush]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-_prune_if_needed]]
- [[eos_ai-substrate-live_sessions-py-_utcnow]]

## Called By

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-_flush]]
- [[eos_ai-substrate-live_sessions-py-attach_pipeline_to_live_session]]
- [[eos_ai-substrate-live_sessions-py-attach_task_to_live_session]]
- [[eos_ai-substrate-live_sessions-py-create_live_session]]
- [[eos_ai-substrate-live_sessions-py-detach_pipeline_from_live_session]]
- [[eos_ai-substrate-live_sessions-py-detach_task_from_live_session]]
- [[eos_ai-substrate-live_sessions-py-end_live_session]]
- [[eos_ai-substrate-live_sessions-py-fail_live_session]]
- [[eos_ai-substrate-live_sessions-py-pause_live_session]]
- [[eos_ai-substrate-live_sessions-py-resume_live_session]]
- [[eos_ai-substrate-live_sessions-py-start_live_session]]
