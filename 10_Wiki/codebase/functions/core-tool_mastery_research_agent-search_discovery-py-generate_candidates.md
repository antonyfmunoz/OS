---
type: codebase-function
file: core/tool_mastery_research_agent/search_discovery.py
line: 326
generated: 2026-05-07
---

# generate_candidates

**File:** [[core-tool_mastery_research_agent-search_discovery-py]] | **Line:** 326
**Signature:** `generate_candidates(tool_slug) → CandidatePlan`

Run every pattern family against the slug and return a plan.

Ordering: the returned ``candidates`` list is grouped by family in
the order declared in ``_FAMILIES`` (vendor first, then API, then
GitHub, then packages). Within each family, lower ``rank`` wins.

## Calls

- [[core-tool_mastery_research_agent-search_discovery-py-_dedupe]]
- [[core-tool_mastery_research_agent-search_discovery-py-_variants]]
