---
type: codebase-function
file: eos_ai/substrate/operator_session.py
line: 256
generated: 2026-05-07
---

# OperatorSessionStore.get

**File:** [[eos_ai-substrate-operator_session-py]] | **Line:** 256
**Signature:** `get() → Optional[OperatorSession]`

**Class:** [[eos_ai-substrate-operator_session-py-OperatorSessionStore]]

Return the current session record, or None if none has been stored.

## Called By

- [[eos_ai-substrate-day_workflows-py-close_day]]
- [[eos_ai-substrate-day_workflows-py-open_day]]
- [[eos_ai-substrate-operator_session-py-OperatorSession-from_dict]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-_load]]
