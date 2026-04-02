# Instagram — EOS Usage Patterns
Source: Meta Developer Docs + EOS operational experience
Last Researched: 2026-04-01

## Official API Rate Limits (Graph API)
- 200 calls/hour per user token
- DM endpoint: requires approved Instagram Messaging permission

## Playwright Monitoring (EOS-specific)
- Login: always use https://www.instagram.com/ root URL (not /accounts/login/)
- Session: store cookies/session after first login to avoid repeated auth
- Detection: VPS IPs get flagged — slow down request rate
- Selector fragility: Instagram UI changes frequently — update selectors when broken

## Bot Detection Patterns (Avoid)
- Fast sequential requests
- Non-standard user agents
- Headless browser fingerprints — use stealth plugins
- Login from new IP without warmup

## EOS Usage Patterns
- DM monitor: runs in os-monitor, checks for new replies on interval
- Lead signal: Apify scrapes post comments → signals → outreach queue
- Outreach: ManyChat handles approved DM sequences, not raw API

## Common Failures and Fixes
- Blank page on login: using /accounts/login/ URL — switch to root URL
- 403 from proxy: RESIDENTIAL credits depleted — disable proxy (INSTAGRAM_USE_PROXY=false)
- Selector not found: Instagram updated UI — update dm_monitor.py selectors
- Session expired: delete session file and re-login

## Version History
- 2026-03-25: confirmed root URL fix for VPS login
- 2026-03-XX: proxy 403 issue documented when RESIDENTIAL credits depleted
