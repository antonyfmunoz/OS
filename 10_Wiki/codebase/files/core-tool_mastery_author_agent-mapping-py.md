---
type: codebase-file
path: core/tool_mastery_author_agent/mapping.py
module: core.tool_mastery_author_agent.mapping
lines: 610
size: 21026
generated: 2026-04-12
---

# core/tool_mastery_author_agent/mapping.py

Section → raw-capture evidence mapping.

The core truthfulness layer. Given a LoadedArtifact (raw HTML/text
captures), the mapper decides which of the 19 TME best_practices
sections have evidence in the captured material — and which do not.
...

**Lines:** 610 | **Size:** 21,026 bytes

## Used By

- [[scripts-measure_phase8_batch-py]]

## Contains

- **class** [[core-tool_mastery_author_agent-mapping-py-SectionEvidence]] — 0 methods
- **fn** [[core-tool_mastery_author_agent-mapping-py-_strip_html]]`(text) → str`
- **fn** [[core-tool_mastery_author_agent-mapping-py-is_prose_block]]`(text) → bool`
- **fn** [[core-tool_mastery_author_agent-mapping-py-_split_prose_blocks]]`(plain) → list[str]`
- **fn** [[core-tool_mastery_author_agent-mapping-py-_excerpt_from_block]]`(block, keyword) → str | None`
- **fn** [[core-tool_mastery_author_agent-mapping-py-_scan_capture_for_section]]`(capture, section, prose_blocks) → tuple[set[str], list[str], int]`
- **fn** [[core-tool_mastery_author_agent-mapping-py-_apply_pattern_evidence]]`(evidence, extracted_patterns) → list[SectionEvidence]`
- **fn** [[core-tool_mastery_author_agent-mapping-py-map_sections]]`(artifact) → list[SectionEvidence]`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from html import unescape
from loader import LoadedArtifact
from loader import RawCapture
```
