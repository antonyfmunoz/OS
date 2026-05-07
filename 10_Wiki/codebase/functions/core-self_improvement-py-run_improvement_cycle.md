---
type: codebase-function
file: core/self_improvement.py
line: 439
generated: 2026-05-07
---

# run_improvement_cycle

**File:** [[core-self_improvement-py]] | **Line:** 439
**Signature:** `run_improvement_cycle(components) → dict[str, Any]`

Run evaluate → propose → apply across specified components.

Returns a summary of all proposals generated and their status.

## Calls

- [[core-self_improvement-py-CompositionImprover-apply_improvements]]
- [[core-self_improvement-py-CompositionImprover-evaluate]]
- [[core-self_improvement-py-CompositionImprover-propose_improvements]]
- [[core-self_improvement-py-PipelineImprover-apply_improvements]]
- [[core-self_improvement-py-PipelineImprover-evaluate]]
- [[core-self_improvement-py-PipelineImprover-propose_improvements]]
- [[core-self_improvement-py-RouterImprover-apply_improvements]]
- [[core-self_improvement-py-RouterImprover-evaluate]]
- [[core-self_improvement-py-RouterImprover-propose_improvements]]
- [[core-self_improvement-py-SelfImprovingComponent-apply_improvements]]
- [[core-self_improvement-py-SelfImprovingComponent-evaluate]]
- [[core-self_improvement-py-SelfImprovingComponent-propose_improvements]]
