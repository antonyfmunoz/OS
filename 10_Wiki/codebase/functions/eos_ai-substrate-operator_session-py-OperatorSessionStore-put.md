---
type: codebase-function
file: eos_ai/substrate/operator_session.py
line: 261
generated: 2026-05-07
---

# OperatorSessionStore.put

**File:** [[eos_ai-substrate-operator_session-py]] | **Line:** 261
**Signature:** `put(session) → None`

**Class:** [[eos_ai-substrate-operator_session-py-OperatorSessionStore]]

Persist a session record.

Sets updated_at on the passed session in place, then flushes to
storage. Flush failures are caught inside _flush() (best-effort).

## Calls

- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-_flush]]
- [[eos_ai-substrate-operator_session-py-_utcnow]]

## Called By

- [[eos_ai-substrate-day_workflows-py-close_day]]
- [[eos_ai-substrate-day_workflows-py-open_day]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-_flush]]
