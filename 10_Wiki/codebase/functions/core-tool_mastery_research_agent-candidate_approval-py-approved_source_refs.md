---
type: codebase-function
file: core/tool_mastery_research_agent/candidate_approval.py
line: 221
generated: 2026-05-07
---

# approved_source_refs

**File:** [[core-tool_mastery_research_agent-candidate_approval-py]] | **Line:** 221
**Signature:** `approved_source_refs(approval) → list[SourceRef]`

Return SourceRefs for only the ``accepted`` candidates.

This is the bridge back into the existing fetch/research flow:
unapproved candidates cannot reach the fetcher through this path.
