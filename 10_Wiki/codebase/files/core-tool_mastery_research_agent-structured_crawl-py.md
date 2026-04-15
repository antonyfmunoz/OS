---
type: codebase-file
path: core/tool_mastery_research_agent/structured_crawl.py
module: core.tool_mastery_research_agent.structured_crawl
lines: 437
size: 15876
generated: 2026-04-12
---

# core/tool_mastery_research_agent/structured_crawl.py

Structured crawl expansion for the Tool Mastery Research Agent.

Phase 3 unlock: some vendor docs sites expose almost no machine-
readable surface (no sitemap, no llms.txt, SPA shell, bot-walled
aggregator search). For those tools, Phases 1 and 2 cannot find
...

**Lines:** 437 | **Size:** 15,876 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-structured_crawl-py-CrawlProvenance]] — 1 methods
- **class** [[core-tool_mastery_research_agent-structured_crawl-py-CrawlReport]] — 1 methods
- **class** [[core-tool_mastery_research_agent-structured_crawl-py-_AnchorExtractor]] — 2 methods
- **fn** [[core-tool_mastery_research_agent-structured_crawl-py-_extract_anchors]]`(body) → list[str]`
- **fn** [[core-tool_mastery_research_agent-structured_crawl-py-_http_get]]`(url) → tuple[bytes | None, str | None]`
- **fn** [[core-tool_mastery_research_agent-structured_crawl-py-_same_host]]`(url, host) → bool`
- **fn** [[core-tool_mastery_research_agent-structured_crawl-py-_looks_like_doc_path]]`(url) → tuple[bool, str]`
- **fn** [[core-tool_mastery_research_agent-structured_crawl-py-_normalise]]`(url) → str`
- **fn** [[core-tool_mastery_research_agent-structured_crawl-py-crawl_approved_docs]]`(approved_refs) → CrawlReport`

## Import Statements

```python
from __future__ import annotations
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from dataclasses import field
from html.parser import HTMLParser
from urllib.parse import urldefrag
from urllib.parse import urljoin
from urllib.parse import urlparse
from docs_site_discovery import _DISCOVERY_SKIP_HOSTS
from docs_site_discovery import _DOC_PATH_HINTS
from docs_site_discovery import _REJECT_PATH_HINTS
from docs_site_discovery import _topically_relevant
from models import SourceRef
from models import SourceTier
```
