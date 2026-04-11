---
type: codebase-file
path: core/tool_mastery_research_agent/source_quality.py
module: core.tool_mastery_research_agent.source_quality
lines: 371
size: 11889
generated: 2026-04-11
---

# core/tool_mastery_research_agent/source_quality.py

Source quality scoring for the Tool Mastery Research Agent.

Two jobs, one module:

1. **Pre-fetch scoring** — classify a candidate source as HIGH or LOW
...

**Lines:** 371 | **Size:** 11,889 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-source_quality-py-SignalReport]] — 1 methods
- **fn** [[core-tool_mastery_research_agent-source_quality-py-_split_host]]`(url) → tuple[str, str]`
- **fn** [[core-tool_mastery_research_agent-source_quality-py-score_source]]`(ref) → str`
- **fn** [[core-tool_mastery_research_agent-source_quality-py-sort_sources_by_quality]]`(sources) → list[tuple[SourceRef, str]]`
- **fn** [[core-tool_mastery_research_agent-source_quality-py-_is_raw_text_source]]`(url) → bool`
- **fn** [[core-tool_mastery_research_agent-source_quality-py-measure_signal]]`() → SignalReport`
- **fn** [[core-tool_mastery_research_agent-source_quality-py-classify_quality]]`(reports) → str`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Iterable
from urllib.parse import urlparse
from models import SourceRef
from models import SourceTier
```
