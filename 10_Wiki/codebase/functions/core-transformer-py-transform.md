---
type: codebase-function
file: core/transformer.py
line: 243
generated: 2026-05-07
---

# transform

**File:** [[core-transformer-py]] | **Line:** 243
**Signature:** `transform(primitives, objective, constraints, context) → TransformationResult`

Analyse and transform a primitive set based on objective + constraints.

Returns a new set (never mutates input). Every addition/removal is
explained in the reasoning list.

...

## Calls

- [[core-primitives-py-validate_composition_tags]]
- [[core-transformer-py-_closure_score]]
- [[core-transformer-py-_completeness_score]]

## Called By

- [[core-feedback-py-apply_feedback]]
- [[core-self_improvement-py-CompositionImprover-propose_improvements]]
- [[core-self_improvement-py-PipelineImprover-propose_improvements]]
