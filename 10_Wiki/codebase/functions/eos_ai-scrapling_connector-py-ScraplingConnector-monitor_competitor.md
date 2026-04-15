---
type: codebase-function
file: eos_ai/scrapling_connector.py
line: 118
generated: 2026-04-12
---

# ScraplingConnector.monitor_competitor

**File:** [[eos_ai-scrapling_connector-py]] | **Line:** 118
**Signature:** `monitor_competitor(url, last_content) → dict`

**Class:** [[eos_ai-scrapling_connector-py-ScraplingConnector]]

Fetch a competitor page and detect content changes.

Args:
    url:          Competitor URL to monitor.
    last_content: Previously stored text to diff against.
...

## Calls

- [[eos_ai-scrapling_connector-py-ScraplingConnector-fetch]]
