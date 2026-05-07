---
type: codebase-function
file: core/matcher.py
line: 306
generated: 2026-05-07
---

# match_for_step

**File:** [[core-matcher-py]] | **Line:** 306
**Signature:** `match_for_step(step_description, primitives, constraints) → CapabilitySelection`

Match a capability for a single pipeline step.

Convenience wrapper that uses the step description as the objective.

## Calls

- [[core-matcher-py-match_capability]]

## Called By

- [[core-router-py-route_execution]]
