---
type: codebase-function
file: core/router.py
line: 120
generated: 2026-05-07
---

# route_execution

**File:** [[core-router-py]] | **Line:** 120
**Signature:** `route_execution(structure, constraints) → ExecutionPlan`

Route a composed structure to per-step capability assignments.

Args:
    structure:     The ComposedStructure from compose().
    constraints:   Budget/latency/quality constraints for matching.
...

## Calls

- [[core-matcher-py-match_for_step]]
- [[core-router-py-_get_step_primitives]]
