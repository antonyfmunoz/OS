---
name: instagram
description: "Use when any agent needs Instagram DM monitoring, comment scraping, session management, or bot detection avoidance for lead generation."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.facebook.com/docs/instagram-api/"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "Instagram Graph API v19.0 / Playwright automation"
sdk_version: "Playwright 1.58.0 (sync API) + Apify actors"
speed_category: "slow"
---

# Tool: Instagram

## What This Tool Does

Instagram access in EOS happens through three distinct paths, each serving a different purpose:

1. **Playwright browser automation** (`dm_monitor.py`) — reads DM inbox, detects replies, extracts messages
2. **Apify cloud scrapers** (`apify_scraper.py`) — scrapes comments from hashtags and competitor posts
3. **ManyChat** — DM automation for approved outreach campaigns (external, not coded in EOS)

The Meta Graph API exists but is not actively used — DM access requires approved Instagram Messaging permission which is not granted for EOS's use case.

## EOS Integration

### Path 1: DM Monitor — Playwright (`services/dm_monitor.py`)

**What it does:**
1. Launches headless Chromium inside Docker (os-monitor container)
2. Restores Instagram session from `storage_state` JSON
3. Navigates to DM inbox (`/direct/inbox/`)
4. Detects unread conversations via DOM selectors
5. Opens each unread thread, extracts messages
6. Feeds extracted messages to AI for sales conversation assistance
7. Takes diagnostic screenshots on failures

**Architecture:**
```
os-monitor container
  └── dm_monitor.py (90-second startup delay)
        └── sync_playwright()
              └── chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
                    └── browser.new_context(storage_state=..., user_agent=..., viewport=...)
                          └── context.new_page()
                                ├── page.goto("https://www.instagram.com/direct/inbox/")
                                ├── page.query_selector_all('a[href*="/direct/t/"]')
                                ├── Extract unread indicators
                                ├── Click thread → extract messages
                                └── context.storage_state(path=...) [save session]
```

**Key config:**
```yaml
# docker-compose.yml
os-monitor:
  shm_size: '2gb'  # Chromium needs this, default 64MB causes SIGBUS
  environment:
    - MONITOR_STARTUP_DELAY=90
    - INSTAGRAM_USE_PROXY=false
```

### Path 2: Comment Scraping — Apify (`services/apify_scraper.py`)

See `skills/tools/apify/SKILL.md` for full details.

**Flow:**
```
Cron → apify_scraper.py
  ├── Hashtag scraping (A/B rotation groups)
  │     → Instagram Hashtag Scraper actor → posts
  │     → Instagram Comment Scraper actor → comments
  │     → Bot/spam filter → priority classification
  │     → Save to 01_Inbox/raw_signals/
  └── Competitor scraping (5 accounts)
        → Instagram Profile Scraper actor → posts
        → Filter by ICP relevance (Whisper + Claude + keywords)
        → Comment scrape → filter → save
```

### Path 3: ManyChat (External)
ManyChat handles approved DM automation sequences.
Not coded in EOS — configured in ManyChat dashboard.
EOS receives booking notifications via Calendly webhooks when ManyChat DMs convert.

### Agents that use it
- DM Monitor (directly — Playwright)
- Scraper Service (directly — Apify)
- EA Agent (indirectly — reads DM Monitor reports)
- Outreach Agent (indirectly — uses signals from scraper)

## Authentication

### Playwright session (DM Monitor)
```python
# Session stored as Playwright storage_state JSON
# Contains both cookies AND localStorage (both required)
instagram_session.json = {
    "cookies": [...],
    "origins": [{
        "origin": "https://www.instagram.com",
        "localStorage": [...]
    }]
}

# Restore session
context = browser.new_context(storage_state="instagram_session.json")

# Save session after successful login
context.storage_state(path="instagram_session.json")
```

### Fresh login flow (when session expires)
```python
# 1. Navigate to root (NOT /accounts/login/ — returns blank from VPS)
page.goto("https://www.instagram.com/")

# 2. Fill credentials (use .type() with delay, NOT .fill() — React inputs)
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type(username, delay=80)
page.locator('input[name="pass"]').click()
page.locator('input[name="pass"]').type(password, delay=80)

# 3. Click login button
page.locator('button:has-text("Log in")').click()

# 4. Handle verification code (relayed via Telegram)
# 5. Dismiss "Save Info" and "Not Now" prompts
# 6. Save session
context.storage_state(path="instagram_session.json")
```

### Environment variables
| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Login email/username |
| `INSTAGRAM_PASSWORD` | Login password |
| `INSTAGRAM_USE_PROXY` | `true` to route through Apify RESIDENTIAL proxy |
| `APIFY_PROXY_PASSWORD` | Proxy auth when proxy enabled |
| `MONITOR_STARTUP_DELAY` | Seconds to wait before first check (default 90) |

## Quick Reference

### Check DM inbox
```python
page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
page.wait_for_selector("div[role='main']", timeout=60000)
threads = page.query_selector_all('a[href*="/direct/t/"]')
```

### Detect unread conversations
```python
# Look for unread indicators (blue dot, bold text)
for thread in threads:
    unread_indicator = thread.query_selector('[data-testid="unread"]')
    # OR check for bold font-weight on thread preview text
```

### Extract messages from thread
```python
thread.click()
page.wait_for_load_state("domcontentloaded")
messages = page.query_selector_all('div[dir="auto"]')
for msg in messages:
    text = msg.inner_text()
```

### Bot detection avoidance
```python
# Human-like timing
import random
time.sleep(random.uniform(2, 5))

# Character-by-character typing (NOT fill())
page.locator('input').type("text", delay=80)

# Desktop Chrome UA (NOT mobile — causes blank page)
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...'

# Viewport matches real browser
viewport = {'width': 1280, 'height': 800}
```

## Gotchas

### Direct /accounts/login/ URL returns blank page (ACTIVE)
Instagram serves a blank page when `/accounts/login/` is accessed from VPS IPs.
**Fix:** Always navigate to root `https://www.instagram.com/` — login form renders correctly.

### Cookie-only session restore triggers bot detection (RESOLVED)
Using only `context.add_cookies()` left sessions incomplete — localStorage was missing.
**Fix:** Use `storage_state()` which saves both cookies AND localStorage.

### React inputs reject fill() (ACTIVE)
Instagram's React-controlled inputs reject synthetic `fill()` events.
**Fix:** Use `click()` + `type(text, delay=80)` for character-by-character input.

### Chromium SIGBUS in Docker (RESOLVED)
Default Docker `/dev/shm` is 64MB. Chromium exceeds this during rendering.
**Fix:** `shm_size: '2gb'` in docker-compose.yml.

### Startup OOM from rapid restart loops (RESOLVED)
Docker `restart: always` caused rapid Chromium restarts (~700MB each), exhausting RAM.
**Fix:** 90-second startup delay (`MONITOR_STARTUP_DELAY=90`) + stale session cleanup.

### Mobile User-Agent causes blank page (RESOLVED)
Mobile Safari UA causes Instagram to serve app-redirect blank page in headless Chromium.
**Fix:** Desktop Chrome UA confirmed to render login form correctly.

### Instagram selector changes break DM extraction (INTERMITTENT)
Instagram updates DOM structure without notice. Selectors for thread links, unread indicators, and message containers break.
**Detection:** DM Monitor reports 0 threads despite known unread messages.
**Fix:** Update selectors in `dm_monitor.py`, test with diagnostic screenshots.

### Apify RESIDENTIAL proxy 403 (ACTIVE)
Proxy credits are separate from compute units. 403 when depleted.
**Fix:** `INSTAGRAM_USE_PROXY=false` until credits refill.

See references/best_practices.md for full session management patterns, anti-detection strategies, and selector reference.
