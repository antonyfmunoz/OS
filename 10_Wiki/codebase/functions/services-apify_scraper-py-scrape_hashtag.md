---
type: codebase-function
file: services/apify_scraper.py
line: 576
generated: 2026-04-12
---

# scrape_hashtag

**File:** [[services-apify_scraper-py]] | **Line:** 576
**Signature:** `scrape_hashtag(hashtag, seen_usernames, seen_comment_texts, counters, client, ignore_cache)`

Scrape posts for a hashtag with smart first-run vs incremental logic.

## Calls

- [[services-apify_scraper-py-_process_comment]]
- [[services-apify_scraper-py-get_post_url]]
- [[services-apify_scraper-py-get_run_results]]
- [[services-apify_scraper-py-is_icp_relevant_post]]
- [[services-apify_scraper-py-is_post_icp_relevant_by_comments]]
- [[services-apify_scraper-py-load_scraped_posts]]
- [[services-apify_scraper-py-poll_run]]
- [[services-apify_scraper-py-run_actor]]
- [[services-apify_scraper-py-save_scraped_posts]]
- [[services-apify_scraper-py-scrape_comments_for_post]]

## Called By

- [[services-apify_scraper-py-main]]
