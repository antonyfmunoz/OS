---
type: codebase-function
file: eos_ai/scrapling_connector.py
line: 34
generated: 2026-04-12
---

# ScraplingConnector.fetch

**File:** [[eos_ai-scrapling_connector-py]] | **Line:** 34
**Signature:** `fetch(url, stealth) → dict`

**Class:** [[eos_ai-scrapling_connector-py-ScraplingConnector]]

Fetch a URL and return structured page data.

Args:
    url:    Target URL.
    stealth: Use StealthyFetcher (default). Set False for lighter Fetcher.
...

## Called By

- [[eos_ai-scrapling_connector-py-ScraplingConnector-monitor_competitor]]
- [[eos_ai-scrapling_connector-py-ScraplingConnector-search_and_fetch]]
