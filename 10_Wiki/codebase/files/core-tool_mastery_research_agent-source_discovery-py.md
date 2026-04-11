---
type: codebase-file
path: core/tool_mastery_research_agent/source_discovery.py
module: core.tool_mastery_research_agent.source_discovery
lines: 363
size: 12846
generated: 2026-04-11
---

# core/tool_mastery_research_agent/source_discovery.py

Source discovery for the Tool Mastery Research Agent.

Given a tool slug, build a prioritised list of primary sources. The
order of preference is:

...

**Lines:** 363 | **Size:** 12,846 bytes

## Contains

- **fn** [[core-tool_mastery_research_agent-source_discovery-py-_slugify]]`(name) → str`
- **fn** [[core-tool_mastery_research_agent-source_discovery-py-_from_registry]]`(slug) → list[SourceRef]`
- **fn** [[core-tool_mastery_research_agent-source_discovery-py-_from_claude_json]]`(slug) → tuple[list[SourceRef], list[str]]`
- **fn** [[core-tool_mastery_research_agent-source_discovery-py-discover_sources]]`(tool_slug) → SourcePlan`

## Import Statements

```python
from __future__ import annotations
import json
import re
from pathlib import Path
from candidate_approval import approved_source_refs
from candidate_approval import latest_approval_file
from candidate_approval import load_approval_file
from docs_site_discovery import discover_docs_site_urls
from docs_site_discovery import parse_site_coordinates
from github_extractor import expand_github_repo
from github_extractor import parse_github_url
from models import SourcePlan
from models import SourceRef
from models import SourceTier
from paths import CLAUDE_JSON
from paths import TOOL_DOC_REGISTRY
from source_quality import SIGNAL_HIGH
from source_quality import SIGNAL_LOW
from source_quality import SIGNAL_MEDIUM
from source_quality import score_source
from source_quality import sort_sources_by_quality
from structured_crawl import crawl_approved_docs
```
