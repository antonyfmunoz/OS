---
type: codebase-function
file: core/tool_mastery_research_agent/docs_site_discovery.py
line: 164
generated: 2026-04-11
---

# parse_site_coordinates

**File:** [[core-tool_mastery_research_agent-docs_site_discovery-py]] | **Line:** 164
**Signature:** `parse_site_coordinates(url) → SiteCoordinates | None`

Return the scheme+host of ``url`` if it's usable, else None.

We deliberately ignore the path — sitemap/llms.txt discovery runs
against the HOST ROOT only. Passing in ``https://vendor.com/docs/x``
still probes ``https://vendor.com/sitemap.xml``.

## Called By

- [[core-tool_mastery_research_agent-docs_site_discovery-py-discover_docs_site_urls]]
