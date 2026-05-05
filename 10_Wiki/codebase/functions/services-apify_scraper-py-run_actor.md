---
type: codebase-function
file: services/apify_scraper.py
line: 239
generated: 2026-04-12
---

# run_actor

**File:** [[services-apify_scraper-py]] | **Line:** 239
**Signature:** `run_actor(actor_id, input_data, retries)`

Start an Apify actor run and return the run ID.

## Calls

- [[services-apify_scraper-py-RateLimiter-wait]]

## Called By

- [[services-apify_scraper-py-scrape_comments_for_post]]
- [[services-apify_scraper-py-scrape_competitor]]
- [[services-apify_scraper-py-scrape_hashtag]]
