---
type: codebase-function
file: core/tool_mastery_research_agent/fetcher.py
line: 46
generated: 2026-04-12
---

# fetch_source

**File:** [[core-tool_mastery_research_agent-fetcher-py]] | **Line:** 46
**Signature:** `fetch_source(ref) → FetchedSource`

Fetch a single SourceRef and write the raw body to ``raw_dir``.

Always returns a FetchedSource — never raises — so callers can
aggregate a honest per-source status.

## Calls

- [[core-tool_mastery_research_agent-fetcher-py-_iso_now]]
- [[core-tool_mastery_research_agent-fetcher-py-_safe_filename]]

## Called By

- [[core-tool_mastery_research_agent-fetcher-py-fetch_plan]]
