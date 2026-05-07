---
type: codebase-class
file: eos_ai/substrate/operator_session.py
line: 206
generated: 2026-05-07
---

# OperatorSessionStore

**File:** [[eos_ai-substrate-operator_session-py]] | **Line:** 206

Durable, thread-safe, singleton store for a single OperatorSession record.

Dual-layer: in-memory + substrate.storage (Neon-backed, JSON fallback).
Best-effort persistence — flush failures log and the in-memory state
remains correct.
...

## Methods

- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-__init__]]`() → None` — 
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-_load]]`() → None` — 
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-_flush]]`() → None` — 
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-get]]`() → Optional[OperatorSession]` — Return the current session record, or None if none has been stored.
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-put]]`(session) → None` — Persist a session record.
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-default]]`() → 'OperatorSessionStore'` — Return the process-level singleton, creating it on first call.
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-reset_default_for_tests]]`() → None` — Tear down the singleton so the next call to default() creates a fresh instance.
