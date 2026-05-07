---
type: codebase-class
file: eos_ai/substrate/live_sessions.py
line: 213
generated: 2026-05-07
---

# LiveSessionStore

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 213

Durable, bounded, thread-safe store for LiveSession records.

Dual-layer: in-memory dict + substrate.storage (Neon-backed, JSON fallback).
Best-effort persistence — flush failures log and the in-memory state
remains correct.
...

## Methods

- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-__init__]]`() → None` — 
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-_load]]`() → None` — 
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-_flush]]`() → None` — Persist in-memory state to substrate storage. Caller holds lock.
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-_prune_if_needed]]`() → None` — Remove oldest ENDED/FAILED sessions if store exceeds _MAX_SESSIONS.
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-get]]`(live_session_id) → Optional[LiveSession]` — Return a session by ID, or None.
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-put]]`(session) → None` — Insert or update a session. Prunes if needed, then flushes to storage.
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-all]]`() → list[LiveSession]` — Return all sessions, sorted by created_at descending (newest first).
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-active]]`() → list[LiveSession]` — Return non-terminal sessions (CREATED, ACTIVE, PAUSED, WAITING_ON_OPERATOR).
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-by_state]]`(state) → list[LiveSession]` — Return sessions matching the given state.
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-by_day_session]]`(day_session_id) → list[LiveSession]` — Return sessions attached to a specific day session.
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-default]]`() → 'LiveSessionStore'` — Return the process-level singleton, creating it on first call.
- [[eos_ai-substrate-live_sessions-py-LiveSessionStore-reset_default_for_tests]]`() → None` — Tear down the singleton so the next call to default() creates a fresh instance.
