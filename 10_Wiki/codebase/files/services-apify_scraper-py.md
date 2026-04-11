---
type: codebase-file
path: services/apify_scraper.py
module: services.apify_scraper
lines: 910
size: 32587
tags: [entry-point]
generated: 2026-04-11
---

# services/apify_scraper.py

> **ENTRY POINT** — Contains `if __name__` or server start.

*No docstring.*

**Lines:** 910 | **Size:** 32,587 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-context-py]]

## Contains

- **class** [[services-apify_scraper-py-RateLimiter]] — 2 methods
- **fn** [[services-apify_scraper-py-_get_whisper_model]]`()`
- **fn** [[services-apify_scraper-py-load_hashtag_config]]`()`
- **fn** [[services-apify_scraper-py-save_hashtag_config]]`(config)`
- **fn** [[services-apify_scraper-py-send_telegram_notification]]`(text)`
- **fn** [[services-apify_scraper-py-should_blacklist]]`(perf_data)`
- **fn** [[services-apify_scraper-py-should_promote]]`(perf_data)`
- **fn** [[services-apify_scraper-py-get_todays_hashtags]]`()`
- **fn** [[services-apify_scraper-py-update_hashtag_performance]]`(counters)`
- **fn** [[services-apify_scraper-py-load_scraped_posts]]`()`
- **fn** [[services-apify_scraper-py-save_scraped_posts]]`(data)`
- **fn** [[services-apify_scraper-py-get_post_url]]`(post)`
- **fn** [[services-apify_scraper-py-run_actor]]`(actor_id, input_data, retries)`
- **fn** [[services-apify_scraper-py-poll_run]]`(run_id)`
- **fn** [[services-apify_scraper-py-get_run_results]]`(run_id, retries)`
- **fn** [[services-apify_scraper-py-is_human_comment]]`(username, text, seen_comment_texts)`
- **fn** [[services-apify_scraper-py-is_priority_comment]]`(text)`
- **fn** [[services-apify_scraper-py-save_signal]]`(username, comment_text, source, post_url, timestamp, priority)`
- **fn** [[services-apify_scraper-py-scrape_comments_for_post]]`(post_url, source, limit)`
- **fn** [[services-apify_scraper-py-_process_comment]]`(comment, source, post_url, seen_usernames, seen_comment_texts, counters)`
- **fn** [[services-apify_scraper-py-is_post_icp_relevant_by_comments]]`(comments, sample_size)`
- **fn** [[services-apify_scraper-py-transcribe_video]]`(video_url)`
- **fn** [[services-apify_scraper-py-is_icp_relevant_post]]`(post, client)`
- **fn** [[services-apify_scraper-py-scrape_hashtag]]`(hashtag, seen_usernames, seen_comment_texts, counters, client, ignore_cache)`
- **fn** [[services-apify_scraper-py-scrape_competitor]]`(account, seen_usernames, seen_comment_texts, counters, client, ignore_cache)`
- **fn** [[services-apify_scraper-py-auto_suggest_hashtags]]`(client)`
- **fn** [[services-apify_scraper-py-main]]`()`

## Import Statements

```python
import os
import re
import sys
import json
import glob
import time
import threading
import requests
import datetime
from dotenv import load_dotenv
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.context import load_context_from_env
```
