---
type: codebase-function
file: core/tool_mastery_research_agent/candidate_approval.py
line: 116
generated: 2026-04-12
---

# persist_approval_file

**File:** [[core-tool_mastery_research_agent-candidate_approval-py]] | **Line:** 116
**Signature:** `persist_approval_file(approval) → Path`

Write the approval file via the Control Plane ``write_file`` action.

Routing through the Control Plane (rather than a bare ``Path.write_text``)
gives us a log entry in ``logs/execution/`` that records *when* the
candidates were generated, by which agent, and with what idempotency
...

## Calls

- [[core-tool_mastery_research_agent-candidate_approval-py-ApprovalFile-to_dict]]
- [[core-tool_mastery_research_agent-candidate_approval-py-CandidateRecord-to_dict]]
- [[core-tool_mastery_research_agent-candidate_approval-py-_candidates_dir]]
