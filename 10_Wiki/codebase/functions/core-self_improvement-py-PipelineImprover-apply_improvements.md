---
type: codebase-function
file: core/self_improvement.py
line: 354
generated: 2026-05-07
---

# PipelineImprover.apply_improvements

**File:** [[core-self_improvement-py]] | **Line:** 354
**Signature:** `apply_improvements(proposals) → dict[str, Any]`

**Class:** [[core-self_improvement-py-PipelineImprover]]

Log pipeline improvement proposals.

## Calls

- [[core-self_improvement-py-CompositionImprover-metrics]]
- [[core-self_improvement-py-CompositionImprover-propose_improvements]]
- [[core-self_improvement-py-ImprovementRecord-to_dict]]
- [[core-self_improvement-py-PipelineImprover-metrics]]
- [[core-self_improvement-py-PipelineImprover-propose_improvements]]
- [[core-self_improvement-py-RouterImprover-metrics]]
- [[core-self_improvement-py-RouterImprover-propose_improvements]]
- [[core-self_improvement-py-SelfImprovingComponent-metrics]]
- [[core-self_improvement-py-SelfImprovingComponent-propose_improvements]]
- [[core-self_improvement-py-_log_improvement]]
- [[core-transformer-py-TransformationResult-to_dict]]

## Called By

- [[core-self_improvement-py-run_improvement_cycle]]
