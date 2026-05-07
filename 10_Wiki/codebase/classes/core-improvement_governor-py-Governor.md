---
type: codebase-class
file: core/improvement_governor.py
line: 86
generated: 2026-05-07
---

# Governor

**File:** [[core-improvement_governor-py]] | **Line:** 86

Manages system self-improvement proposals.

Low-risk changes are auto-applied and logged.
Medium/high-risk changes are written as proposals for human review.
All changes are auditable and reversible.

## Methods

- [[core-improvement_governor-py-Governor-__init__]]`() → None` — 
- [[core-improvement_governor-py-Governor-propose]]`(target_component, proposed_change, reason, risk_level) → ImprovementProposal` — Create an improvement proposal.
- [[core-improvement_governor-py-Governor-approve]]`(proposal_id) → ImprovementProposal | None` — Approve and apply a pending proposal.
- [[core-improvement_governor-py-Governor-reject]]`(proposal_id, reason) → ImprovementProposal | None` — Reject a pending proposal.
- [[core-improvement_governor-py-Governor-rollback]]`(proposal_id) → ImprovementProposal | None` — Roll back an applied proposal.
- [[core-improvement_governor-py-Governor-get_pending]]`() → list[ImprovementProposal]` — Return all pending proposals awaiting approval.
- [[core-improvement_governor-py-Governor-get_applied]]`() → list[ImprovementProposal]` — Return all applied proposals.
- [[core-improvement_governor-py-Governor-get_all]]`() → list[ImprovementProposal]` — Return all proposals.
- [[core-improvement_governor-py-Governor-propose_from_objective_results]]`(objective_results, aggregate_score) → list[ImprovementProposal]` — Generate proposals based on multi-objective evaluation results.
- [[core-improvement_governor-py-Governor-propose_from_strategy]]`(strategy, current_context) → ImprovementProposal | None` — Propose adopting a successful strategy pattern.
- [[core-improvement_governor-py-Governor-_find]]`(proposal_id) → ImprovementProposal | None` — 
- [[core-improvement_governor-py-Governor-_write_proposal]]`(proposal) → None` — Write proposal to filesystem for human review.
- [[core-improvement_governor-py-Governor-_log]]`(proposal, event) → None` — Append to audit log.
