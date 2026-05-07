---
type: codebase-function
file: eos_ai/substrate/live_sessions.py
line: 518
generated: 2026-05-07
---

# attach_pipeline_to_live_session

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 518
**Signature:** `attach_pipeline_to_live_session(live_session_id, pipeline_id) → LiveSession`

Attach a pipeline to a live session. Deduplicates.

Raises ValueError if session not found.

## Calls

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]
- [[eos_ai-substrate-live_sessions-py-_get_and_validate]]
- [[eos_ai-substrate-live_sessions-py-_log]]
