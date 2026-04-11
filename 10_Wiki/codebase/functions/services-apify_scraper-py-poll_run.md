---
type: codebase-function
file: services/apify_scraper.py
line: 264
generated: 2026-04-11
---

# poll_run

**File:** [[services-apify_scraper-py]] | **Line:** 264
**Signature:** `poll_run(run_id)`

Poll until run is SUCCEEDED or FAILED. Returns final status.

## Calls

- [[services-apify_scraper-py-RateLimiter-wait]]

## Called By

- [[services-apify_scraper-py-scrape_comments_for_post]]
- [[services-apify_scraper-py-scrape_competitor]]
- [[services-apify_scraper-py-scrape_hashtag]]
