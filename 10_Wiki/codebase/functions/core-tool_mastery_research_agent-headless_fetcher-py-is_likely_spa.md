---
type: codebase-function
file: core/tool_mastery_research_agent/headless_fetcher.py
line: 81
generated: 2026-04-11
---

# is_likely_spa

**File:** [[core-tool_mastery_research_agent-headless_fetcher-py]] | **Line:** 81
**Signature:** `is_likely_spa(raw_bytes) → tuple[bool, str]`

Return (is_spa, reason) for a static HTML body.

Two independent triggers, either sufficient:

1. **Framework marker**: an explicit Next.js/Nuxt/Docusaurus/etc.
...
