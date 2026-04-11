---
type: codebase-function
file: eos_ai/ceo_agent.py
line: 165
generated: 2026-04-11
---

# CEOAgent.reason_org_chart

**File:** [[eos_ai-ceo_agent-py]] | **Line:** 165
**Signature:** `reason_org_chart(primitives) → list[str]`

**Class:** [[eos_ai-ceo_agent-py-CEOAgent]]

AI-powered org chart reasoning.
Not a static map — reasons from actual primitives to determine
which roles the company needs RIGHT NOW at this exact stage.

Falls back to STAGE_ROLE_MAP if AI call fails.

## Calls

- [[eos_ai-ceo_agent-py-CEOAgent-detect_primitives]]

## Called By

- [[eos_ai-ceo_agent-py-CEOAgent-check_and_evolve]]
- [[eos_ai-ceo_agent-py-CEOAgent-spin_up_org]]
