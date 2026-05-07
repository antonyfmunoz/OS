---
type: codebase-file
path: core/tool_mastery_research_agent/fetcher.py
module: core.tool_mastery_research_agent.fetcher
lines: 164
size: 5274
generated: 2026-05-07
---

# core/tool_mastery_research_agent/fetcher.py

Fetcher for the Tool Mastery Research Agent.

Thin, dependency-free HTTP GET over urllib. No HTML parsing, no
browser emulation, no LLM calls. Writes raw captures to disk under
the run directory for full provenance.
...

**Lines:** 164 | **Size:** 5,274 bytes

## Contains

- **fn** [[core-tool_mastery_research_agent-fetcher-py-_iso_now]]`() → str`
- **fn** [[core-tool_mastery_research_agent-fetcher-py-_safe_filename]]`(url, index) → str`
- **fn** [[core-tool_mastery_research_agent-fetcher-py-fetch_source]]`(ref) → FetchedSource`
- **fn** [[core-tool_mastery_research_agent-fetcher-py-fetch_plan]]`(sources) → list[FetchedSource]`

## Import Statements

```python
from __future__ import annotations
import socket
import urllib.error
import urllib.request
from datetime import datetime
from datetime import timezone
from pathlib import Path
from urllib.parse import urlparse
from models import FetchedSource
from models import FetchStatus
from models import SourceRef
```
