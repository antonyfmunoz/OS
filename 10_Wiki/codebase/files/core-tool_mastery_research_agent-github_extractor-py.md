---
type: codebase-file
path: core/tool_mastery_research_agent/github_extractor.py
module: core.tool_mastery_research_agent.github_extractor
lines: 349
size: 12308
generated: 2026-05-07
---

# core/tool_mastery_research_agent/github_extractor.py

GitHub repo extractor for the Tool Mastery Research Agent.

Phase 1 unlock: when source discovery yields a ``github.com/owner/repo``
URL, that URL alone is almost worthless — the landing page is a
JS-heavy SPA shell that the signal gate correctly drops. The *actual*
...

**Lines:** 349 | **Size:** 12,308 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-github_extractor-py-RepoCoordinates]] — 0 methods
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-parse_github_url]]`(url) → RepoCoordinates | None`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-_api_get_json]]`(url) → tuple[dict | list | None, str | None]`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-_get_default_branch_sha]]`(coords) → tuple[str | None, str | None, str | None]`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-_list_tree]]`(coords, sha) → tuple[list[dict], str | None]`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-_path_in_any_dir]]`(path, prefixes) → bool`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-_prioritise_files]]`(entries) → list[str]`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-_raw_url]]`(coords, sha, path) → str`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-_classify_label]]`(path) → str`
- **fn** [[core-tool_mastery_research_agent-github_extractor-py-expand_github_repo]]`(ref) → tuple[list[SourceRef], list[str]]`

## Import Statements

```python
from __future__ import annotations
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse
from models import SourceRef
from models import SourceTier
```
