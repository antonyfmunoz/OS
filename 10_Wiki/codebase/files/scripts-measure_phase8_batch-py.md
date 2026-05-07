---
type: codebase-file
path: scripts/measure_phase8_batch.py
module: scripts.measure_phase8_batch
lines: 336
size: 12003
tags: [entry-point]
generated: 2026-05-07
---

# scripts/measure_phase8_batch.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Phase 8 batch measurement — full re-extraction.

For each of the 8 benchmark tools:
1. Loads the latest research artifact JSON + raw captures from disk
2. Re-runs extraction with *current* Phase 8 code on every OK raw capture
...

**Lines:** 336 | **Size:** 12,003 bytes

## Depends On

- [[core-tool_mastery_author_agent-draft-py]]
- [[core-tool_mastery_author_agent-loader-py]]
- [[core-tool_mastery_author_agent-mapping-py]]
- [[core-tool_mastery_research_agent-artifact-py]]
- [[core-tool_mastery_research_agent-extraction-py]]

## Contains

- **class** [[scripts-measure_phase8_batch-py-ToolResult]] — 0 methods
- **fn** [[scripts-measure_phase8_batch-py-find_latest_artifact]]`(tool) → Path | None`
- **fn** [[scripts-measure_phase8_batch-py-_load_raw_captures_from_disk]]`(run_dir) → list[RawCapture]`
- **fn** [[scripts-measure_phase8_batch-py-re_extract_patterns]]`(loaded, fallback_raw) → dict[str, list[dict[str, Any]]]`
- **fn** [[scripts-measure_phase8_batch-py-measure_tool]]`(tool) → ToolResult`
- **fn** [[scripts-measure_phase8_batch-py-main]]`()`

## Import Statements

```python
import json
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from core.tool_mastery_author_agent.loader import LoadedArtifact
from core.tool_mastery_author_agent.loader import RawCapture
from core.tool_mastery_author_agent.loader import load_artifact
from core.tool_mastery_author_agent.loader import sanitize_text
from core.tool_mastery_author_agent.mapping import _split_prose_blocks
from core.tool_mastery_author_agent.mapping import _strip_html
from core.tool_mastery_author_agent.mapping import map_sections
from core.tool_mastery_author_agent.draft import build_drafts
from core.tool_mastery_research_agent.artifact import TME_SECTIONS
from core.tool_mastery_research_agent.extraction import extract_from_source
from core.tool_mastery_research_agent.extraction import merge_extractions
```
