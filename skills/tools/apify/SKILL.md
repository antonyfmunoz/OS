---
name: apify-tool
description: "Apify scraping integration for EOS. Use when research_agent needs Instagram comment signals or any web scraping task."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://docs.apify.com/api/v2"
last_researched: "2026-04-01"
effort: low
---

# Tool: Apify

## What This Tool Does
Apify is a cloud scraping platform. EOS uses it primarily for Instagram comment scraping
to feed the ICP signal pipeline.

## EOS Integration
- services/apify_scraper.py — runs Apify actors for Instagram comments
- Signals pipeline: comments → analyze_icp_signal → detect_icp_patterns → market report
- APIFY_API_TOKEN in services/.env
- INSTAGRAM_USE_PROXY=true flag routes through Apify RESIDENTIAL proxy

## Key Actors in Use
- instagram-comment-scraper — scrapes comments from target posts
- Proxy group: RESIDENTIAL (credits tracked — 403 when depleted)

## Quick Reference
```python
from apify_client import ApifyClient

client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
run = client.actor("apify/instagram-comment-scraper").call(
    run_input={"postUrls": [...], "resultsLimit": 100}
)
results = client.dataset(run["defaultDatasetId"]).iterate_items()
```

See references/best_practices.md for rate limits and credit management.
