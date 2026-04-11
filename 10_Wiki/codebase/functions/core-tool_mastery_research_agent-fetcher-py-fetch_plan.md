---
type: codebase-function
file: core/tool_mastery_research_agent/fetcher.py
line: 134
generated: 2026-04-11
---

# fetch_plan

**File:** [[core-tool_mastery_research_agent-fetcher-py]] | **Line:** 134
**Signature:** `fetch_plan(sources) → list[FetchedSource]`

Fetch sources in order, capped by ``max_fetches``.

Sources beyond the cap are recorded as SKIPPED so the provenance
remains honest ("we saw it, we chose not to spend a fetch on it")
rather than silently disappearing from the run.

## Calls

- [[core-tool_mastery_research_agent-fetcher-py-_iso_now]]
- [[core-tool_mastery_research_agent-fetcher-py-fetch_source]]
