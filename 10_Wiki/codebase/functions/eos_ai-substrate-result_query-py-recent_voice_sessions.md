---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 304
generated: 2026-04-12
---

# recent_voice_sessions

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 304
**Signature:** `recent_voice_sessions(limit, node_id) → list[dict]`

Most recent voice sessions, newest-first. JSON-friendly. Bounded.

Read-only view over VoiceSessionStore — exists here so operator scripts
can pull all "what happened recently" lookups from one module.

## Calls

- [[eos_ai-substrate-result_query-py-latest]]
- [[eos_ai-substrate-result_store-py-IngestedResult-as_dict]]
- [[eos_ai-substrate-result_store-py-ResultStore-latest]]

## Called By

- [[scripts-substrate_voice_session_smoke_test-py-main]]
