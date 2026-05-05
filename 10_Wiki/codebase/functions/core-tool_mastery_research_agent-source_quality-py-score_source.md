---
type: codebase-function
file: core/tool_mastery_research_agent/source_quality.py
line: 141
generated: 2026-04-12
---

# score_source

**File:** [[core-tool_mastery_research_agent-source_quality-py]] | **Line:** 141
**Signature:** `score_source(ref) → str`

Classify a candidate source as high / medium / low signal.

The scoring is intentionally coarse. Tiebreakers go to *low* —
we'd rather deprioritize an honest high-signal source than let a
marketing page through.

## Calls

- [[core-tool_mastery_research_agent-source_quality-py-_split_host]]

## Called By

- [[core-tool_mastery_research_agent-source_quality-py-sort_sources_by_quality]]
