---
type: codebase-function
file: core/capabilities.py
line: 110
generated: 2026-05-07
---

# Capability.effective_quality

**File:** [[core-capabilities-py]] | **Line:** 110
**Signature:** `effective_quality() → float`

**Class:** [[core-capabilities-py-Capability]]

Quality adjusted by observed success rate.

Blends the static baseline with live performance.  Early on
(< 10 runs) the baseline dominates; as data accumulates the
observed rate takes over.

## Called By

- [[core-capabilities-py-Capability-to_dict]]
- [[core-matcher-py-_constraint_fit_score]]
- [[core-matcher-py-match_capability]]
