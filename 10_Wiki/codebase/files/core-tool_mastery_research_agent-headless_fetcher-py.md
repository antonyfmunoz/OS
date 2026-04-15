---
type: codebase-file
path: core/tool_mastery_research_agent/headless_fetcher.py
module: core.tool_mastery_research_agent.headless_fetcher
lines: 367
size: 13508
generated: 2026-04-12
---

# core/tool_mastery_research_agent/headless_fetcher.py

Headless rendering fetch path for the Tool Mastery Research Agent.

Phase 4 unlock: docs sites built as client-rendered SPAs (Next.js,
Docusaurus, Mintlify, Nuxt, etc.) return an empty shell to urllib.
The prose lives in hydrated DOM, not the HTTP body. This module
...

**Lines:** 367 | **Size:** 13,508 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-headless_fetcher-py-RenderAttempt]] — 1 methods
- **class** [[core-tool_mastery_research_agent-headless_fetcher-py-RenderPassReport]] — 1 methods
- **fn** [[core-tool_mastery_research_agent-headless_fetcher-py-_iso_now]]`() → str`
- **fn** [[core-tool_mastery_research_agent-headless_fetcher-py-is_likely_spa]]`(raw_bytes) → tuple[bool, str]`
- **fn** [[core-tool_mastery_research_agent-headless_fetcher-py-_load_playwright]]`()`
- **fn** [[core-tool_mastery_research_agent-headless_fetcher-py-_render_one]]`(playwright_ctx, url) → tuple[bytes, str | None]`
- **fn** [[core-tool_mastery_research_agent-headless_fetcher-py-render_low_signal_sources]]`() → tuple[list[FetchedSource], RenderPassReport]`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from models import FetchedSource
from models import FetchStatus
```
