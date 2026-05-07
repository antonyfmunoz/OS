---
type: codebase-function
file: eos_ai/ceo_agent.py
line: 239
generated: 2026-05-07
---

# CEOAgent.evaluate_stage_transition

**File:** [[eos_ai-ceo_agent-py]] | **Line:** 239
**Signature:** `evaluate_stage_transition(primitives) → bool`

**Class:** [[eos_ai-ceo_agent-py-CEOAgent]]

Check whether the company has crossed a stage upgrade threshold.
Stage gates mirror STAGE_PROOF_GATES from business_instance.py.

## Called By

- [[eos_ai-ceo_agent-py-CEOAgent-check_and_evolve]]
