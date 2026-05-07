---
type: codebase-function
file: core/self_improvement.py
line: 332
generated: 2026-05-07
---

# PipelineImprover.propose_improvements

**File:** [[core-self_improvement-py]] | **Line:** 332
**Signature:** `propose_improvements() → list[TransformationResult]`

**Class:** [[core-self_improvement-py-PipelineImprover]]

Propose primitive-level improvements based on pipeline failures.

## Calls

- [[core-self_improvement-py-CompositionImprover-evaluate]]
- [[core-self_improvement-py-PipelineImprover-evaluate]]
- [[core-self_improvement-py-RouterImprover-evaluate]]
- [[core-self_improvement-py-SelfImprovingComponent-evaluate]]
- [[core-transformer-py-transform]]

## Called By

- [[core-self_improvement-py-CompositionImprover-apply_improvements]]
- [[core-self_improvement-py-PipelineImprover-apply_improvements]]
- [[core-self_improvement-py-run_improvement_cycle]]
