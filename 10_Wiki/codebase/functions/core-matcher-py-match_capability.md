---
type: codebase-function
file: core/matcher.py
line: 211
generated: 2026-05-07
---

# match_capability

**File:** [[core-matcher-py]] | **Line:** 211
**Signature:** `match_capability(primitives, objective, constraints) → CapabilitySelection`

Select the best capability for executing a primitive composition.

Args:
    primitives:   Active L0 primitive tags.
    objective:    Natural-language description of the goal.
...

## Calls

- [[core-capabilities-py-Capability-effective_quality]]
- [[core-capabilities-py-list_capabilities]]
- [[core-matcher-py-_constraint_fit_score]]
- [[core-matcher-py-_derive_required_tasks]]
- [[core-matcher-py-_task_fit_score]]

## Called By

- [[core-matcher-py-match_for_step]]
