---
type: codebase-function
file: core/tool_mastery_research_agent/extraction.py
line: 300
generated: 2026-05-07
---

# classify_source_type

**File:** [[core-tool_mastery_research_agent-extraction-py]] | **Line:** 300
**Signature:** `classify_source_type() → SourceTypeReport`

Classify a fetched body into one of five Phase-5 source types.

``sanitized_text`` is the Author-Agent-style scrubbed HTML (still
contains tags). ``plain_text`` is the tag-stripped form used for
vocabulary density. ``prose_chars`` is the already-measured prose
...

## Calls

- [[core-tool_mastery_research_agent-extraction-py-_count_vocab_hits]]

## Called By

- [[core-tool_mastery_research_agent-extraction-py-extract_from_source]]
