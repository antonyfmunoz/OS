---
type: codebase-function
file: core/primitives.py
line: 171
generated: 2026-05-07
---

# validate_primitive_set

**File:** [[core-primitives-py]] | **Line:** 171
**Signature:** `validate_primitive_set(tags) → list[str]`

Check a set of primitive tags for structural issues.

Returns a list of warnings (empty = valid).  Checks:
1. No unknown tags (enforced by enum, but belt-and-suspenders).
2. No duplicate tags (set guarantees this, included for API clarity).
...

## Called By

- [[core-primitives-py-validate_composition_tags]]
