---
type: codebase-function
file: core/tool_mastery_research_agent/candidate_approval.py
line: 182
generated: 2026-04-12
---

# apply_decision

**File:** [[core-tool_mastery_research_agent-candidate_approval-py]] | **Line:** 182
**Signature:** `apply_decision(approval) → ApprovalFile`

Mutate an ApprovalFile in place with the operator's decisions.

Indexes are 1-based to match the CLI display. Any candidate not
explicitly named remains ``pending`` unless ``accept_all`` or
``reject_all`` is set.

## Calls

- [[core-tool_mastery_research_agent-candidate_approval-py-_now_iso]]
