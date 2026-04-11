---
type: codebase-file
path: core/tool_mastery_research_agent/docs_site_discovery.py
module: core.tool_mastery_research_agent.docs_site_discovery
lines: 610
size: 21349
generated: 2026-04-11
---

# core/tool_mastery_research_agent/docs_site_discovery.py

Docs site discovery for the Tool Mastery Research Agent.

Phase 2 unlock: many vendor docs sites are JS-rendered SPAs whose root
HTML contains nothing but a bootstrap <script>. Phase 1's GitHub repo
extractor solved the repo case, but sites like clo3d.com, higgsfield.ai,
...

**Lines:** 610 | **Size:** 21,349 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-docs_site_discovery-py-SiteCoordinates]] — 1 methods
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-parse_site_coordinates]]`(url) → SiteCoordinates | None`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_http_get]]`(url) → tuple[bytes | None, str | None, str | None]`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_looks_like_doc_path]]`(url) → bool`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_parse_sitemap_xml]]`(body) → tuple[list[str], list[str], str | None]`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_parse_llms_txt]]`(body, base) → list[str]`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_same_host]]`(url, host) → bool`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_discover_via_sitemap]]`(coords) → tuple[list[str], list[str]]`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_discover_via_llms_txt]]`(coords) → tuple[list[str], bool, list[str]]`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_topically_relevant]]`(url, tool_slug) → bool`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-_filter_and_rank]]`(urls, host) → list[str]`
- **fn** [[core-tool_mastery_research_agent-docs_site_discovery-py-discover_docs_site_urls]]`(ref) → tuple[list[SourceRef], list[str]]`

## Import Statements

```python
from __future__ import annotations
import re
import socket
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urljoin
from urllib.parse import urlparse
from models import SourceRef
from models import SourceTier
```
