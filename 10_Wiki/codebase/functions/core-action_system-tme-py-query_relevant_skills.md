---
type: codebase-function
file: core/action_system/tme.py
line: 31
generated: 2026-04-11
---

# query_relevant_skills

**File:** [[core-action_system-tme-py]] | **Line:** 31
**Signature:** `query_relevant_skills(term) → dict`

Run `query_skills.py search <term>` and return a dict with the raw output.

Never raises — TME is advisory, not load-bearing for Control Plane v1.
