---
type: codebase-function
file: eos_ai/substrate/day_workflows.py
line: 350
generated: 2026-05-07
---

# close_day

**File:** [[eos_ai-substrate-day_workflows-py]] | **Line:** 350
**Signature:** `close_day() → dict`

Close the operator's day session and write continuity for the next open.

If no open session exists, returns {"status": "not_open"}. Otherwise
starts a CLOSE_DAY ritual (best-effort), writes all continuity fields,
sets is_day_open=False, and persists.
...

## Calls

- [[eos_ai-substrate-day_workflows-py-_advance_ritual_best_effort]]
- [[eos_ai-substrate-day_workflows-py-_log]]
- [[eos_ai-substrate-day_workflows-py-_start_ritual_best_effort]]
- [[eos_ai-substrate-day_workflows-py-_today_str]]
- [[eos_ai-substrate-day_workflows-py-_utcnow]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-default]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-get]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-put]]
- [[eos_ai-substrate-operator_session-py-_log]]
- [[eos_ai-substrate-operator_session-py-_utcnow]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-default]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-get]]
- [[eos_ai-substrate-rituals-py-_utcnow]]
