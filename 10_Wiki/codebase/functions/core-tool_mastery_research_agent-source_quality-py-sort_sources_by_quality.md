---
type: codebase-function
file: core/tool_mastery_research_agent/source_quality.py
line: 202
generated: 2026-04-11
---

# sort_sources_by_quality

**File:** [[core-tool_mastery_research_agent-source_quality-py]] | **Line:** 202
**Signature:** `sort_sources_by_quality(sources) → list[tuple[SourceRef, str]]`

Return sources paired with their score, high signal first.

Stable on the input order within each signal band — so the caller's
existing ordering (registry > MCP > generated) is preserved within
bands.

## Calls

- [[core-tool_mastery_research_agent-source_quality-py-score_source]]
