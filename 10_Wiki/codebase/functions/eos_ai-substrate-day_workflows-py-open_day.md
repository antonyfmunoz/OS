---
type: codebase-function
file: eos_ai/substrate/day_workflows.py
line: 93
generated: 2026-05-07
---

# open_day

**File:** [[eos_ai-substrate-day_workflows-py]] | **Line:** 93
**Signature:** `open_day() → dict`

Open the operator's day session.

If the day is already open, returns an already_open response with no
state mutation and no new ritual. Otherwise creates a new OperatorSession,
inherits continuity from the prior session, starts an OPEN_DAY ritual
...

## Calls

- [[eos_ai-substrate-day_workflows-py-_advance_ritual_best_effort]]
- [[eos_ai-substrate-day_workflows-py-_log]]
- [[eos_ai-substrate-day_workflows-py-_start_ritual_best_effort]]
- [[eos_ai-substrate-day_workflows-py-_today_str]]
- [[eos_ai-substrate-day_workflows-py-_utcnow]]
- [[eos_ai-substrate-operator_session-py-OperatorSession-new]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-default]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-get]]
- [[eos_ai-substrate-operator_session-py-OperatorSessionStore-put]]
- [[eos_ai-substrate-operator_session-py-_log]]
- [[eos_ai-substrate-operator_session-py-_utcnow]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-default]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-get]]
- [[eos_ai-substrate-rituals-py-_utcnow]]
