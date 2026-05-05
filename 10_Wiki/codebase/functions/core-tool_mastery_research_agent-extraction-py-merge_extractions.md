---
type: codebase-function
file: core/tool_mastery_research_agent/extraction.py
line: 1200
generated: 2026-04-12
---

# merge_extractions

**File:** [[core-tool_mastery_research_agent-extraction-py]] | **Line:** 1200
**Signature:** `merge_extractions(extractions) → dict[str, list[dict[str, Any]]]`

Fold per-source extractions into the artifact's flat bucket layout.

Output shape matches the artifact contract:
    {
        "usage":    [{...}, ...],
...

## Calls

- [[core-tool_mastery_research_agent-extraction-py-ExtractedPattern-to_dict]]
- [[core-tool_mastery_research_agent-extraction-py-SourceExtraction-to_dict]]
- [[core-tool_mastery_research_agent-extraction-py-SourceTypeReport-to_dict]]

## Called By

- [[scripts-measure_phase8_batch-py-re_extract_patterns]]
