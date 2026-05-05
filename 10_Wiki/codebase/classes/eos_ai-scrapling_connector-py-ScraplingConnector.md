---
type: codebase-class
file: eos_ai/scrapling_connector.py
line: 26
generated: 2026-04-12
---

# ScraplingConnector

**File:** [[eos_ai-scrapling_connector-py]] | **Line:** 26

Stealth web fetcher using Scrapling under the hood.

StealthyFetcher (default) — uses Playwright with stealth patches.
Fetcher (fallback) — curl_cffi based, lighter, less stealth.

## Methods

- [[eos_ai-scrapling_connector-py-ScraplingConnector-fetch]]`(url, stealth) → dict` — Fetch a URL and return structured page data.
- [[eos_ai-scrapling_connector-py-ScraplingConnector-search_and_fetch]]`(query, num_results) → list[dict]` — Search Google and fetch the top organic results.
- [[eos_ai-scrapling_connector-py-ScraplingConnector-monitor_competitor]]`(url, last_content) → dict` — Fetch a competitor page and detect content changes.
