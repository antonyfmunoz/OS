---
type: codebase-function
file: eos_ai/substrate/local_listener.py
line: 249
generated: 2026-04-12
---

# LocalListener.start_voice_session

**File:** [[eos_ai-substrate-local_listener-py]] | **Line:** 249
**Signature:** `start_voice_session(node_id, role_slug)`

**Class:** [[eos_ai-substrate-local_listener-py-LocalListener]]

Start a bounded voice session on `node_id` with `role_slug`.

Returns the VoiceSession (always — failures are persisted as ERROR
sessions, exactly like LocalTrigger ERROR statuses). Never raises.

...

## Calls

- [[eos_ai-substrate-local_listener-py-_log]]
- [[eos_ai-substrate-ritual_body-py-_log]]
- [[eos_ai-substrate-storage-py-_log]]

## Called By

- [[scripts-substrate_voice_session_smoke_test-py-main]]
