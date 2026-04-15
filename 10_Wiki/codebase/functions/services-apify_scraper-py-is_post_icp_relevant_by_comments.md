---
type: codebase-function
file: services/apify_scraper.py
line: 466
generated: 2026-04-12
---

# is_post_icp_relevant_by_comments

**File:** [[services-apify_scraper-py]] | **Line:** 466
**Signature:** `is_post_icp_relevant_by_comments(comments, sample_size)`

Check if a post's comment section contains ICP signals.
Returns True (relevant), False (not relevant), or None (can't tell — pass through).

## Called By

- [[services-apify_scraper-py-scrape_competitor]]
- [[services-apify_scraper-py-scrape_hashtag]]
