---
type: codebase-function
file: core/feedback.py
line: 213
generated: 2026-05-07
---

# evaluate_result

**File:** [[core-feedback-py]] | **Line:** 213
**Signature:** `evaluate_result(result, context) → FeedbackSignal`

Convert a PipelineResult into a primitive-level FeedbackSignal.

Analyses each step's outcome and maps it back to the primitives
that step exercises.  The result is a diagnosis at the primitive level.

## Calls

- [[core-feedback-py-_compute_step_score]]
- [[core-feedback-py-_get_step_primitives]]
