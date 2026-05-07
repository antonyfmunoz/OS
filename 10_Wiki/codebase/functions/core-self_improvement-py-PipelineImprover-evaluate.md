---
type: codebase-function
file: core/self_improvement.py
line: 303
generated: 2026-05-07
---

# PipelineImprover.evaluate

**File:** [[core-self_improvement-py]] | **Line:** 303
**Signature:** `evaluate() → dict[str, Any]`

**Class:** [[core-self_improvement-py-PipelineImprover]]

Diagnose pipeline health.

## Calls

- [[core-self_improvement-py-CompositionImprover-metrics]]
- [[core-self_improvement-py-PipelineImprover-metrics]]
- [[core-self_improvement-py-RouterImprover-metrics]]
- [[core-self_improvement-py-SelfImprovingComponent-metrics]]

## Called By

- [[core-self_improvement-py-CompositionImprover-propose_improvements]]
- [[core-self_improvement-py-PipelineImprover-propose_improvements]]
- [[core-self_improvement-py-run_improvement_cycle]]
