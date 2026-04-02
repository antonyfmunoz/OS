---
name: instagram-tool
description: "Instagram DM monitoring and outreach for EOS. Use when outreach_agent needs to send DMs or dm_monitor needs to track replies."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.facebook.com/docs/instagram-api/"
last_researched: "2026-04-01"
---

# Tool: Instagram

## What This Tool Does
Instagram access via two paths:
1. Playwright browser automation (dm_monitor.py) — reads DM inbox, detects replies
2. Meta Graph API — official API for business accounts with approved permissions

EOS currently uses Playwright path for DM monitoring (bot detection constraints apply).

## EOS Integration
- services/dm_monitor.py — Playwright-based inbox monitor (os-monitor Docker service)
- Apify scraper — comment scraping for lead signals
- ManyChat — DM automation for approved campaigns
- INSTAGRAM_USE_PROXY flag in services/.env (default: no proxy)

## Authentication
- Playwright: session stored in Instagram session files
- Graph API: access token in services/.env as INSTAGRAM_ACCESS_TOKEN
- Login URL: use root https://www.instagram.com/ (not /accounts/login/ — returns blank from VPS)

## Key Constraints
- Bot detection is aggressive from VPS IPs
- Direct /accounts/login/ URL returns blank — always use root URL
- Proxy (Apify RESIDENTIAL group) returns 403 when credits depleted

See references/best_practices.md for session management and detection avoidance.
