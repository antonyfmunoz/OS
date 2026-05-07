---
type: codebase-file
path: core/tool_mastery_research_agent/agent.py
module: core.tool_mastery_research_agent.agent
lines: 199
size: 6965
generated: 2026-05-07
---

# core/tool_mastery_research_agent/agent.py

Research Agent orchestrator.

Glues discovery → fetch → artifact → handoff into a single run, and
writes a run manifest so every execution is auditable.

**Lines:** 199 | **Size:** 6,965 bytes

## Contains

- **fn** [[core-tool_mastery_research_agent-agent-py-_run_stamp]]`() → str`
- **fn** [[core-tool_mastery_research_agent-agent-py-_derive_status]]`(fetched_count, ok_count) → ResearchStatus`
- **fn** [[core-tool_mastery_research_agent-agent-py-_queue_author_action]]`() → dict[str, object]`
- **fn** [[core-tool_mastery_research_agent-agent-py-run]]`(request) → ResearchResult`

## Import Statements

```python
from __future__ import annotations
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from artifact import build_artifact
from artifact import write_artifact
from fetcher import fetch_plan
from handoff import apply_safe_metadata
from models import FetchStatus
from models import ResearchRequest
from models import ResearchResult
from models import ResearchStatus
from paths import RESEARCH_LOG_DIR
from source_discovery import discover_sources
```
