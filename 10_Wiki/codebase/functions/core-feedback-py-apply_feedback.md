---
type: codebase-function
file: core/feedback.py
line: 346
generated: 2026-05-07
---

# apply_feedback

**File:** [[core-feedback-py]] | **Line:** 346
**Signature:** `apply_feedback(primitives, feedback, objective) → tuple[set[PrimitiveTag], TransformationResult]`

Apply a feedback signal to produce an improved primitive set.

Uses the transformer engine with constraints derived from the feedback.
Returns both the improved set and the full transformation trace.

## Calls

- [[core-transformer-py-transform]]
