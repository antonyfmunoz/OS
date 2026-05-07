---
type: codebase-function
file: eos_ai/ceo_agent.py
line: 268
generated: 2026-05-07
---

# CEOAgent.check_and_evolve

**File:** [[eos_ai-ceo_agent-py]] | **Line:** 268
**Signature:** `check_and_evolve() → dict`

**Class:** [[eos_ai-ceo_agent-py-CEOAgent]]

Full evolution cycle.
Detects primitives → checks stage gate → evolves org if threshold crossed.
Returns changes dict with transition details and Discord message.
Idempotent — safe to call daily.

## Calls

- [[eos_ai-ceo_agent-py-CEOAgent-detect_primitives]]
- [[eos_ai-ceo_agent-py-CEOAgent-evaluate_stage_transition]]
- [[eos_ai-ceo_agent-py-CEOAgent-reason_org_chart]]
- [[eos_ai-ceo_agent-py-CEOAgent-spin_up_org]]
