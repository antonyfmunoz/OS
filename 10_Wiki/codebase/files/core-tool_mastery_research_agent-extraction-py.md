---
type: codebase-file
path: core/tool_mastery_research_agent/extraction.py
module: core.tool_mastery_research_agent.extraction
lines: 1266
size: 43005
generated: 2026-04-11
---

# core/tool_mastery_research_agent/extraction.py

Structured knowledge extraction for the Tool Mastery Research Agent.

Phase 5 of the research agent. Where Phase 1–4 focused on *access* (find,
fetch, render, filter), Phase 5 focuses on *understanding*: converting
raw prose and rendered docs into structured, reusable mastery knowledge.
...

**Lines:** 1266 | **Size:** 43,005 bytes

## Used By

- [[scripts-measure_phase8_batch-py]]

## Contains

- **class** [[core-tool_mastery_research_agent-extraction-py-SourceType]] — 0 methods
- **class** [[core-tool_mastery_research_agent-extraction-py-SourceTypeReport]] — 1 methods
- **class** [[core-tool_mastery_research_agent-extraction-py-ExtractedPattern]] — 1 methods
- **class** [[core-tool_mastery_research_agent-extraction-py-SourceExtraction]] — 2 methods
- **fn** [[core-tool_mastery_research_agent-extraction-py-preprocess_for_extraction]]`(raw_text) → str`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_count_vocab_hits]]`(text_lower, vocab) → int`
- **fn** [[core-tool_mastery_research_agent-extraction-py-classify_source_type]]`() → SourceTypeReport`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_heading_with_body]]`(plain, match, max_chars) → str`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_bounded]]`(text) → str`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_confidence]]`(occurrences, structured) → str`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_emit_if_worthy]]`() → ExtractedPattern | None`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_install_commands]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_setup_flows]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_config_blocks]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_function_signatures]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_param_defs]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_json_schemas]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_workflow_sequences]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_version_pins]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_design_intent]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_operational_behavior]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-_extract_conceptual_model]]`(plain, url) → list[ExtractedPattern]`
- **fn** [[core-tool_mastery_research_agent-extraction-py-extract_from_source]]`() → SourceExtraction`
- **fn** [[core-tool_mastery_research_agent-extraction-py-merge_extractions]]`(extractions) → dict[str, list[dict[str, Any]]]`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from html import unescape
from typing import Any
from typing import Iterable
from urllib.parse import urlparse
```
