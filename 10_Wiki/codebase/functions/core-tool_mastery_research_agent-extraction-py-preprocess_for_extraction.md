---
type: codebase-function
file: core/tool_mastery_research_agent/extraction.py
line: 87
generated: 2026-04-12
---

# preprocess_for_extraction

**File:** [[core-tool_mastery_research_agent-extraction-py]] | **Line:** 87
**Signature:** `preprocess_for_extraction(raw_text) → str`

Code-preserving HTML → structured text pass for pattern extraction.

Strips only the things we *never* want (scripts, styles, noscript)
while leaving code fences, JSON blobs, install commands, and
parameter tables fully intact.
...

## Called By

- [[core-tool_mastery_research_agent-extraction-py-extract_from_source]]
