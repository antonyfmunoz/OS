---
type: codebase-function
file: core/tool_mastery_research_agent/headless_fetcher.py
line: 224
generated: 2026-05-07
---

# render_low_signal_sources

**File:** [[core-tool_mastery_research_agent-headless_fetcher-py]] | **Line:** 224
**Signature:** `render_low_signal_sources() → tuple[list[FetchedSource], RenderPassReport]`

Re-capture low-signal candidates using a headless browser.

``candidates`` are the FetchedSource records that currently sit at
status OK but whose static body looks like an SPA shell — the
caller (artifact.build_artifact) is responsible for filtering down
...

## Calls

- [[core-tool_mastery_research_agent-headless_fetcher-py-_iso_now]]
- [[core-tool_mastery_research_agent-headless_fetcher-py-_load_playwright]]
- [[core-tool_mastery_research_agent-headless_fetcher-py-_render_one]]
