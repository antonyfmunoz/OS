---
type: codebase-class
file: core/tool_mastery_research_agent/structured_crawl.py
line: 82
generated: 2026-04-12
---

# CrawlProvenance

**File:** [[core-tool_mastery_research_agent-structured_crawl-py]] | **Line:** 82

Why a particular URL was kept by the crawler.

This is attached to each emitted SourceRef.origin string so that
downstream debugging can trace the decision path without reading
the crawl code.

## Methods

- [[core-tool_mastery_research_agent-structured_crawl-py-CrawlProvenance-to_origin]]`(host) → str` — 

## Decorators

- `@dataclass`
