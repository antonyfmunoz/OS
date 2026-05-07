---
type: codebase-file
path: core/tool_mastery_research_agent/artifact.py
module: core.tool_mastery_research_agent.artifact
lines: 609
size: 22716
generated: 2026-05-07
---

# core/tool_mastery_research_agent/artifact.py

Artifact writer for the Tool Mastery Research Agent.

Takes a list of FetchedSource objects and produces three on-disk
artifacts:

...

**Lines:** 609 | **Size:** 22,716 bytes

## Used By

- [[scripts-measure_phase8_batch-py]]

## Contains

- **fn** [[core-tool_mastery_research_agent-artifact-py-_iso_now]]`() → str`
- **fn** [[core-tool_mastery_research_agent-artifact-py-_ok_sources]]`(sources) → list[FetchedSource]`
- **fn** [[core-tool_mastery_research_agent-artifact-py-_run_signal_pass]]`(ok_sources) → tuple[list[SignalReport], set[str]]`
- **fn** [[core-tool_mastery_research_agent-artifact-py-_run_phase5_extraction]]`() → tuple[list[SourceExtraction], dict[str, str]]`
- **fn** [[core-tool_mastery_research_agent-artifact-py-build_artifact]]`() → ResearchArtifact`
- **fn** [[core-tool_mastery_research_agent-artifact-py-_render_summary]]`(artifact, plan) → str`
- **fn** [[core-tool_mastery_research_agent-artifact-py-_render_sources]]`(artifact) → str`
- **fn** [[core-tool_mastery_research_agent-artifact-py-write_artifact]]`(run_dir, artifact, plan) → dict[str, str]`

## Import Statements

```python
from __future__ import annotations
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from extraction import SourceExtraction
from extraction import SourceType
from extraction import extract_from_source
from extraction import merge_extractions
from headless_fetcher import RenderPassReport
from headless_fetcher import is_likely_spa
from headless_fetcher import render_low_signal_sources
from models import FetchedSource
from models import FetchStatus
from models import ResearchArtifact
from models import ResearchMode
from models import SourcePlan
from source_quality import SignalReport
from source_quality import classify_quality
from source_quality import measure_signal
```
