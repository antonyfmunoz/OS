---
type: codebase-function
file: core/tool_mastery_author_agent/mapping.py
line: 541
generated: 2026-04-11
---

# map_sections

**File:** [[core-tool_mastery_author_agent-mapping-py]] | **Line:** 541
**Signature:** `map_sections(artifact) → list[SectionEvidence]`

Scan each section against all raw captures.

A section is marked ``sourced=True`` only when its keyword set
hits at least ``MIN_KEYWORD_HITS`` distinct keywords across the
available captures. One-hit matches are treated as insufficient
...

## Calls

- [[core-tool_mastery_author_agent-mapping-py-_apply_pattern_evidence]]
- [[core-tool_mastery_author_agent-mapping-py-_scan_capture_for_section]]
- [[core-tool_mastery_author_agent-mapping-py-_split_prose_blocks]]
- [[core-tool_mastery_author_agent-mapping-py-_strip_html]]

## Called By

- [[scripts-measure_phase8_batch-py-measure_tool]]
