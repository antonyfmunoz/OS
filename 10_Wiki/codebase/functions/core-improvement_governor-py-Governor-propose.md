---
type: codebase-function
file: core/improvement_governor.py
line: 102
generated: 2026-05-07
---

# Governor.propose

**File:** [[core-improvement_governor-py]] | **Line:** 102
**Signature:** `propose(target_component, proposed_change, reason, risk_level) → ImprovementProposal`

**Class:** [[core-improvement_governor-py-Governor]]

Create an improvement proposal.

Low-risk proposals are auto-applied.
Medium/high-risk proposals require approval.

## Calls

- [[core-improvement_governor-py-Governor-_log]]
- [[core-improvement_governor-py-Governor-_write_proposal]]

## Called By

- [[core-improvement_governor-py-Governor-propose_from_objective_results]]
- [[core-improvement_governor-py-Governor-propose_from_strategy]]
