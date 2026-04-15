---
type: codebase-function
file: scripts/measure_phase8_batch.py
line: 114
generated: 2026-04-12
---

# re_extract_patterns

**File:** [[scripts-measure_phase8_batch-py]] | **Line:** 114
**Signature:** `re_extract_patterns(loaded, fallback_raw) → dict[str, list[dict[str, Any]]]`

Re-run Phase 5+7+8 extraction on all raw captures using current code.

## Calls

- [[core-tool_mastery_author_agent-loader-py-sanitize_text]]
- [[core-tool_mastery_author_agent-mapping-py-_split_prose_blocks]]
- [[core-tool_mastery_author_agent-mapping-py-_strip_html]]
- [[core-tool_mastery_research_agent-extraction-py-extract_from_source]]
- [[core-tool_mastery_research_agent-extraction-py-merge_extractions]]

## Called By

- [[scripts-measure_phase8_batch-py-measure_tool]]
