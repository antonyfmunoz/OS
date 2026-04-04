# Instagram — Best Practices (Creator-Level Reference)

Source: Meta Developer Docs + Playwright automation patterns + EOS production experience
Version: Instagram Graph API v19.0 / Playwright 1.58.0 automation
Last Researched: 2026-04-04

---

## 1. Authentication

### Playwright session (DM Monitor — primary path)
```python
# Save session (cookies + localStorage)
context.storage_state(path="instagram_session.json")

# Restore session
context = browser.new_context(storage_state="instagram_session.json")

# Session file structure:
{
    "cookies": [
        {"name": "sessionid", "value": "...", "domain": ".instagram.com", ...},
        {"name": "csrftoken", "value": "...", "domain": ".instagram.com", ...},
        ...
    ],
    "origins": [
        {
            "origin": "https://www.instagram.com",
            "localStorage": [
                {"name": "ig_did", "value": "..."},
                {"name": "datr", "value": "..."},
                ...
            ]
        }
    ]
}
```

**Critical:** Both cookies AND localStorage are required. Cookie-only restore triggers bot detection.

### Fresh login flow
```python
# 1. Navigate to ROOT URL (NOT /accounts/login/)
page.goto("https://www.instagram.com/", wait_until="domcontentloaded")

# 2. Wait for login form
page.wait_for_selector('input[name="email"]', timeout=30000)

# 3. Fill credentials (character-by-character, NOT fill())
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type(username, delay=80)
page.locator('input[name="pass"]').click()
page.locator('input[name="pass"]').type(password, delay=80)

# 4. Click login
page.locator('button:has-text("Log in")').click()

# 5. Handle two-factor auth (verification code)
# Code relayed via Telegram or file-based mechanism

# 6. Dismiss "Save Your Login Info?" prompt
page.locator('button:has-text("Not Now")').click()

# 7. Dismiss "Turn On Notifications?" prompt
page.locator('button:has-text("Not Now")').click()

# 8. Save session
context.storage_state(path="instagram_session.json")
```

### Graph API auth (not actively used)
```python
# Access token in services/.env
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

# Token types:
# - User token: for user's own data (60-day expiry)
# - Page token: for business account data (never expires)
# - App token: for public data only

# Required permissions for DM access:
# instagram_manage_messages (requires Meta app review)
```

### Environment variables
| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Login email/username |
| `INSTAGRAM_PASSWORD` | Login password |
| `INSTAGRAM_ACCESS_TOKEN` | Graph API token (not actively used) |
| `INSTAGRAM_USE_PROXY` | `true` to use Apify RESIDENTIAL proxy |
| `APIFY_PROXY_PASSWORD` | Proxy auth |
| `MONITOR_STARTUP_DELAY` | Seconds before first check (default 90) |

---

## 2. Core Operations with Exact Signatures

### Navigate to DM inbox
```python
page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
page.wait_for_selector("div[role='main']", timeout=60000)
```

### Find DM threads
```python
# All thread links in inbox
threads = page.query_selector_all('a[href*="/direct/t/"]')

# Thread URL format: /direct/t/{thread_id}/
# Thread ID is numeric: e.g., /direct/t/340282366841710300949128103432/
```

### Detect unread threads
```python
# Method 1: Look for unread indicator elements
for thread in threads:
    unread = thread.query_selector('[data-testid="unread"]')
    # Or check for bold font-weight on preview text
    
# Method 2: Compare thread list against known/processed threads
```

### Extract messages from thread
```python
thread.click()
page.wait_for_load_state("domcontentloaded")
time.sleep(random.uniform(1, 3))  # Human-like delay

# Message text containers
messages = page.query_selector_all('div[dir="auto"]')
for msg in messages:
    text = msg.inner_text()
    
# Message metadata (sender, time) varies by DOM structure
# Instagram updates these selectors frequently
```

### Take diagnostic screenshot
```python
page.screenshot(path="/opt/OS/logs/dm_monitor_screenshot.png")
# Full page:
page.screenshot(path="/opt/OS/logs/full.png", full_page=True)
```

### Graph API endpoints (reference — not actively used by EOS)
```
# User profile
GET /v19.0/{user-id}?fields=id,username,name,biography,followers_count

# User media
GET /v19.0/{user-id}/media?fields=id,caption,media_type,timestamp,like_count,comments_count

# Comments on media
GET /v19.0/{media-id}/comments?fields=id,text,username,timestamp

# DM conversations (requires instagram_manage_messages)
GET /v19.0/{ig-user-id}/conversations

# Rate limits:
# 200 calls/hour per user token
# 4800 calls/day per business user
```

---

## 3. Pagination Patterns

### Playwright: scroll-based pagination
```python
# Instagram DM inbox uses infinite scroll
# To load more threads:
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
time.sleep(2)
# Then re-query for new thread elements

# For message history within a thread:
# Scroll up to load older messages
thread_container = page.query_selector("div[role='main']")
thread_container.evaluate("el => el.scrollTop = 0")
```

### Graph API: cursor pagination
```python
# Initial request
response = requests.get(
    f"https://graph.instagram.com/v19.0/{media_id}/comments",
    params={"fields": "id,text,username", "limit": 50, "access_token": token},
)
data = response.json()
comments = data["data"]

# Next page
while "next" in data.get("paging", {}):
    response = requests.get(data["paging"]["next"])
    data = response.json()
    comments.extend(data["data"])
```

### Apify: resultsLimit
```python
# Apify actors handle pagination internally
# Just set resultsLimit in actor input
run_actor(actor_id, {"directUrls": [url], "resultsLimit": 100})
```

---

## 4. Rate Limits

### Graph API rate limits
| Endpoint | Limit | Window |
|----------|-------|--------|
| General | 200 calls/hour | Per user token |
| Business Discovery | 200 calls/hour | Per business user |
| Content Publishing | 25 posts/day | Per business account |
| DM API | 200 calls/hour | Requires approved permission |

### Playwright automation rate limits (self-imposed)
```python
# EOS anti-detection timing
MONITOR_STARTUP_DELAY = 90       # seconds before first check
random.uniform(2, 5)              # between page navigations
delay=80                          # milliseconds per character typed
random.uniform(1, 3)              # between thread opens
time.sleep(5)                     # after login success
```

**Instagram detection signals (avoid these):**
- More than 60 actions/hour (likes, follows, DM reads)
- Less than 2 seconds between page navigations
- Automated typing speed (< 50ms per character)
- Consistent timing patterns (always exactly N seconds)
- Non-standard viewport sizes or user agents

### Apify scraping rate
```python
# apify_scraper.py
API_DELAY = 2          # seconds between API calls
POLL_INTERVAL = 5      # seconds between status polls
calls_per_minute = 10  # rate limiter setting
```

---

## 5. Error Codes and Recovery

### Instagram HTTP responses (Playwright context)
| Scenario | Symptom | Recovery |
|----------|---------|----------|
| Session expired | Redirect to login page | Re-login flow |
| Bot detection | Challenge page or 403 | Wait, use proxy, manual verify |
| Rate limited | 429 or temporary block | Wait 1-24 hours |
| IP blocked | Blank page or CAPTCHA | Switch to proxy |
| Checkpoint required | Verification code page | Relay code via Telegram |
| Account disabled | Error page | Cannot recover automatically |

### Graph API error codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 4 | Rate limit | Wait and retry |
| 10 | Permissions error | Check token scopes |
| 17 | Account rate limit | Wait 1 hour |
| 100 | Invalid parameter | Check field names |
| 190 | Invalid/expired token | Refresh token |
| 200 | Permission denied | Request permission in Meta app |
| 368 | Temporarily blocked | Wait 24 hours |

### EOS error handling patterns
```python
# Session validation
try:
    page.goto("https://www.instagram.com/direct/inbox/")
    page.wait_for_selector('a[href*="/direct/t/"]', timeout=15000)
    # Session valid
except:
    # Session expired → re-login
    _fresh_login(page, context)

# Screenshot on any failure
except Exception as e:
    page.screenshot(path=f"/opt/OS/logs/error_{timestamp}.png")
    raise
```

---

## 6. SDK Idioms

### Playwright sync API (EOS pattern)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'],
    )
    context = browser.new_context(
        storage_state="instagram_session.json",
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
        viewport={'width': 1280, 'height': 800},
        locale='en-US',
        timezone_id='America/Los_Angeles',
    )
    page = context.new_page()
```

### Multi-selector fallback (DOM fragility)
```python
# Instagram changes selectors frequently
# Use fallback chains:
email_input = (
    page.query_selector('input[name="email"]') or
    page.query_selector('input[name="username"]') or
    page.query_selector('input[aria-label="Phone number, username, or email"]')
)

login_button = (
    page.query_selector('button[type="submit"]') or
    page.query_selector('button:has-text("Log in")') or
    page.query_selector('div[role="button"]:has-text("Log in")')
)
```

### Human-like interaction patterns
```python
# Random delays between actions
import random
time.sleep(random.uniform(2, 5))

# Character-by-character typing
page.locator('input').type("text", delay=80)

# Don't clear before typing — click then type
page.locator('input').click()
page.locator('input').type("text", delay=80)

# Random mouse movements (if needed)
page.mouse.move(random.randint(100, 500), random.randint(100, 400))
```

---

## 7. Anti-Patterns

### 1. Using /accounts/login/ URL
```python
# WRONG — returns blank page from VPS IPs
page.goto("https://www.instagram.com/accounts/login/")

# RIGHT — root URL renders login form
page.goto("https://www.instagram.com/")
```

### 2. Using fill() for React inputs
```python
# WRONG — React's onChange doesn't fire
page.locator('input[name="email"]').fill("user@example.com")

# RIGHT — character-by-character typing
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type("user@example.com", delay=80)
```

### 3. Cookie-only session restore
```python
# WRONG — triggers bot detection
context.add_cookies(saved_cookies)

# RIGHT — save and restore full state
context = browser.new_context(storage_state="session.json")
```

### 4. Fast sequential actions
```python
# WRONG — looks automated
for thread in threads:
    thread.click()
    extract_messages(page)

# RIGHT — human-like timing
for thread in threads:
    time.sleep(random.uniform(2, 5))
    thread.click()
    time.sleep(random.uniform(1, 3))
    extract_messages(page)
```

### 5. Mobile user agent
```python
# WRONG — causes app-redirect blank page
user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS ...)"

# RIGHT — desktop Chrome UA
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ..."
```

### 6. Hardcoded selectors without fallback
```python
# WRONG — breaks when Instagram updates DOM
page.query_selector('div.x1fymye3')  # class-based selectors are unstable

# RIGHT — semantic selectors with fallback
page.query_selector('a[href*="/direct/t/"]')  # URL-based, more stable
```

### 7. No startup delay in Docker
```python
# WRONG — rapid restart loops cause OOM
# Docker restart: always + Chromium 700MB = RAM exhaustion

# RIGHT — 90-second startup delay
startup_delay = int(os.getenv("MONITOR_STARTUP_DELAY", 90))
time.sleep(startup_delay)
```

---

## 8. Data Model

### Instagram entity model (relevant to EOS)
```
Account
  └── Profile (username, bio, followers_count)
  └── Posts (media_id, caption, timestamp, likes, comments_count)
        └── Comments (text, username, timestamp, likes)
  └── Stories (not scraped by EOS)
  └── Direct Messages
        └── Threads (thread_id, participants)
              └── Messages (text, sender, timestamp, seen)
```

### EOS data flow — DM Monitor
```
Chromium → Instagram DM inbox
  → Thread list (a[href*="/direct/t/"])
    → Unread detection
      → Thread open → message extraction
        → AI analysis (model_router)
          → Response suggestion
            → Notification to founder
```

### EOS data flow — Comment Scraping
```
Apify actor → Instagram posts
  → Comments (per post)
    → Bot filter → Spam filter → Dedup
      → Priority classification
        → Signal markdown files (01_Inbox/raw_signals/)
          → Lead qualification pipeline
```

### Session state
```
instagram_session.json
  ├── cookies[] — session auth
  │     ├── sessionid — primary auth token
  │     ├── csrftoken — CSRF protection
  │     ├── ds_user_id — user ID
  │     └── ... (~20 cookies)
  └── origins[].localStorage[] — client state
        ├── ig_did — device ID
        └── ... (~10 items)
```

---

## 9. Webhooks and Events

### Instagram webhooks (Graph API — not used by EOS)
```
# Requires Meta App with approved permissions
# Webhook topics:
# - messages (DM messages)
# - messaging_postbacks
# - messaging_optins
# - messaging_referrals

# EOS cannot use webhooks because:
# 1. instagram_manage_messages permission not approved
# 2. DM Monitor uses Playwright (browser automation), not API
```

### EOS internal event flow
```
DM Monitor detects new message
  → Extracts text and sender
  → Sends to model_router for AI analysis
  → Stores response suggestion
  → Notifies founder via:
    ├── Discord (if DISCORD_BRIEF_WEBHOOK set)
    └── Telegram (send_telegram())
```

---

## 10. Limits

### Instagram platform limits
| Resource | Limit | Notes |
|----------|-------|-------|
| DMs per day | ~50-80 | From new accounts, varies by trust score |
| Actions per hour | ~60 | Likes, follows, DM opens combined |
| Login attempts | ~5/hour | Before temporary lock |
| Account age for DMs | 30+ days | New accounts can't send DMs |
| Message length | ~1000 chars | DM message limit |
| Stories per day | 100 | Not relevant to EOS |

### EOS Playwright limits
| Resource | Limit | Notes |
|----------|-------|-------|
| Concurrent browsers | 1 | Single Chromium instance per container |
| Browser memory | ~700 MB | Chromium base usage |
| Docker shm_size | 2 GB | Required for Chromium rendering |
| Startup delay | 90 seconds | Prevents OOM from restart loops |
| Session validity | ~24-72 hours | Before re-login needed |

### Apify scraping limits
| Resource | Limit | Notes |
|----------|-------|-------|
| Comments per post | 100-200 | `resultsLimit` in actor input |
| Posts per hashtag | 10-50 | First run: 50, updates: 10 |
| Competitors monitored | 5 | Hardcoded in `COMPETITOR_ACCOUNTS` |

---

## 11. Cost Model

### Playwright (DM Monitor) — free
Playwright runs locally in Docker. No external API costs.
Only cost: VPS compute for Chromium (~700 MB RAM).

### Apify scraping — pay per compute
See `skills/tools/apify/SKILL.md` for detailed cost model.
Typical daily scrape: 0.20-0.50 CU (~$0.10-0.25).
RESIDENTIAL proxy: ~$10/GB.

### Claude Haiku for relevance filtering
```python
# Per-post relevance check: ~$0.00025/call
# Per-run: 20-50 posts × $0.00025 = $0.005-0.0125
# Monthly: $0.15-0.375
```

### Graph API — free
Instagram Graph API is free for approved apps.
Rate-limited but no per-call cost.

---

## 12. Version Pinning

### Playwright
```bash
# Installed in Dockerfile
pip install playwright==1.58.0
playwright install chromium --with-deps

# Chromium version tied to Playwright version
# Updating Playwright may change Chromium behavior
```

### Instagram DOM (no version pinning possible)
Instagram updates its DOM without notice. Selectors that work today may break tomorrow.
**Strategy:** Use semantic selectors (href patterns, aria labels, role attributes) over class-based selectors. Always have fallback chains.

### Graph API versioning
```
# Version in URL path
GET /v19.0/{user-id}/media

# Version deprecation: ~2 years per version
# Current: v19.0 (2024)
# Always specify version explicitly
```

---

## 13. Design Intent and Tradeoffs

### Why Playwright over Graph API
The Graph API requires Meta app review for DM access (`instagram_manage_messages`).
This permission is only granted to businesses with a clear messaging use case
and Meta approval. EOS's use case (monitoring DMs for sales leads) doesn't qualify.

Playwright bypasses this by automating a real browser session — the same as a human user.

**Tradeoffs:**
- Pro: No permission requirements, full DM access
- Con: Fragile (DOM changes), slower, resource-heavy (Chromium in Docker)
- Con: Bot detection risk, session expiry, selector maintenance

### Why Apify over custom scraping
Building and maintaining Instagram scrapers requires constant selector updates.
Apify community actors are maintained by their authors and handle Instagram's
frequent DOM changes. EOS gets updated scraping capability without maintenance burden.

**Tradeoffs:**
- Pro: Maintained by community, handles edge cases
- Con: External dependency, actor can be deprecated
- Con: Field names can change between versions

### Why A/B hashtag rotation
Testing all hashtags simultaneously would require too many API calls.
A/B rotation limits daily API usage while still covering the full set.
Performance data drives automatic optimization over time.

---

## 14. Problem-Solution Map and Hidden Capabilities

### Session expires during long monitoring session
**Problem:** Instagram invalidates sessions after extended headless usage.
**Solution:** Save `storage_state()` after every successful interaction.
On next check, restore and validate. If invalid, trigger re-login flow.

### Verification code challenge during login
**Problem:** Instagram sends SMS/email verification code.
**Solution:** Code relay via Telegram. DM Monitor writes expected code
to a file, which is manually provided by founder via Telegram command.

### Bot detection from VPS IP
**Problem:** VPS datacenter IPs are flagged by Instagram.
**Solution:** Apify RESIDENTIAL proxy provides real ISP IPs.
Sticky sessions keep the same IP for the duration of monitoring.
```python
proxy = {
    'server': 'http://proxy.apify.com:8000',
    'username': f'groups-RESIDENTIAL,session-{random_id},country-US',
    'password': proxy_password,
}
```

### DM inbox infinite scroll
**Problem:** Only recent threads visible without scrolling.
**Solution:** `page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`
followed by sleep to let new threads load. Repeat until no new threads appear.

### Distinguishing sent vs received messages
**Problem:** DOM doesn't clearly label message direction.
**Solution:** Check message container alignment or CSS classes.
Messages from the account owner are typically right-aligned.
Combined with sender name extraction where available.

---

## 15. Operational Behavior and Edge Cases

### Instagram login from new IP triggers challenge
First login from VPS IP always triggers a verification challenge.
After successful verification + session save, subsequent restores don't trigger it.
Session typically valid for 24-72 hours.

### Headless Chromium detected as bot
Instagram uses multiple signals to detect headless browsers:
- Navigator.webdriver property
- Missing browser plugins
- Canvas fingerprinting
- WebGL renderer string

Playwright's default Chromium handles most of these, but not all.
Using `--disable-blink-features=AutomationControlled` can help.

### DOM structure changes after Instagram A/B tests
Instagram runs frequent A/B tests that change the DOM for a subset of users.
The same account may see different HTML on different days.
**Mitigation:** Use multiple selector strategies with fallbacks.

### Session file grows over time
`storage_state()` captures ALL localStorage, including analytics data.
Files can grow to 50+ KB. This doesn't affect functionality but wastes disk.

### Chromium crash recovery in Docker
If Chromium crashes (SIGBUS, OOM), the Docker container restarts.
The 90-second startup delay prevents rapid restart loops.
`_clear_stale_chromium_session()` cleans up old user-data directories.

---

## 16. Ecosystem Position and Composition

### Where Instagram fits in EOS
```
Lead Generation:
  Instagram comments ← Apify scrapers ← apify_scraper.py
    └── Raw signals → 01_Inbox/ → lead qualification → CRM

DM Monitoring:
  Instagram DMs ← Playwright ← dm_monitor.py
    └── Unread messages → AI analysis → response suggestions → notifications

Outreach:
  ManyChat (external) → DM sequences → Calendly booking → webhook → pipeline
```

### Interfaces
- **With Playwright:** Browser automation for DM access
- **With Apify:** Cloud scraping for comments and posts
- **With ManyChat:** External DM automation (not coded in EOS)
- **With Claude/Gemini:** AI analysis of extracted messages
- **With Calendly:** Booking link in outreach → webhook triggers pipeline
- **With Telegram:** Verification code relay, monitoring notifications
- **With Discord:** Alert notifications for new DM replies

---

## 17. Trajectory and Evolution

### Current state (2026-04)
- Playwright DM Monitor: operational but fragile (selector-dependent)
- Apify comment scraping: self-optimizing pipeline with A/B testing
- ManyChat outreach: external, manual configuration
- Graph API: not used (permission not approved)

### Potential improvements
- **Graph API approval:** If Meta approves messaging permission, replace Playwright with API calls
- **Stealth browser:** Use playwright-extra with stealth plugin for better anti-detection
- **Content creation API:** Instagram Content Publishing API for automated posting
- **Stories monitoring:** Extend DM Monitor to check story replies
- **AI-powered response:** Auto-draft DM responses (currently manual)

### Risks
- Instagram increases bot detection → Playwright path becomes unreliable
- Apify actors deprecated → need to find/build replacements
- Meta tightens Graph API access → fewer data sources
- Account suspension from automated activity

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Three channels, one pipeline
Instagram is not one integration — it's three:
1. **DM inbox** (Playwright) — direct conversation with leads
2. **Public comments** (Apify) — signal mining from stranger conversations
3. **Outreach sequences** (ManyChat) — automated initial contact

All three feed into the same lead pipeline:
Signal → Qualification → CRM → Booking → Call → Close

### Recipe: Debug DM Monitor not detecting messages
```bash
# 1. Check container is running
docker logs os-monitor --tail 20

# 2. Take manual screenshot
# SSH to VPS, exec into container:
docker exec os-monitor python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(storage_state='/app/services/instagram_session.json')
    page = context.new_page()
    page.goto('https://www.instagram.com/direct/inbox/')
    page.wait_for_load_state('domcontentloaded')
    page.screenshot(path='/app/logs/debug_inbox.png')
    print('Screenshot saved')
    browser.close()
"

# 3. Check screenshot for:
# - Login page? → Session expired, need re-login
# - Challenge page? → Verification needed
# - Blank page? → Try with proxy
# - Inbox visible but no unread? → Selectors may have changed
```

### Recipe: Force re-login
```bash
# 1. Delete session file
rm /opt/OS/services/instagram_session.json

# 2. Restart monitor (will trigger fresh login)
docker restart os-monitor

# 3. Watch logs for verification code prompt
docker logs os-monitor -f

# 4. Relay verification code via Telegram when prompted
```

---

## 19. Industry Expert and Cutting-Edge Usage

### Multi-signal lead qualification
EOS doesn't just scrape comments — it builds a lead quality score from multiple signals:

```
Comment text → Priority keyword match (buyer language)
  + Username analysis → Bot detection (pattern matching)
    + Post context → ICP relevance (Whisper + Claude + keywords)
      + Hashtag performance → Source quality (auto-blacklist/promote)
        = Qualified lead signal with priority classification
```

This multi-layer approach reduces false positives and surfaces
the highest-value leads from massive volumes of raw data.

### Anti-detection strategy
EOS combines multiple techniques to avoid Instagram bot detection:

1. **Session persistence:** Don't log in every time — restore valid sessions
2. **Desktop UA:** Mobile UA triggers app-redirect, desktop renders correctly
3. **Human timing:** Random delays (2-5s), character-by-character typing (80ms)
4. **Residential proxy:** Real ISP IPs when direct VPS IP is blocked
5. **Startup delay:** 90 seconds prevents rapid restart fingerprinting
6. **Viewport + locale:** Match real browser dimensions and timezone

### Self-healing scraping pipeline
The comment scraping pipeline has built-in self-optimization:
- **Auto-blacklist:** Low-performing hashtags removed after 3 runs
- **Auto-promote:** High-performing hashtags elevated to Group A after 2 runs
- **Weekly AI suggestions:** Claude Haiku proposes new hashtags based on what's working
- **Cache management:** Only new posts processed, URLs tracked per source
- **Cost tracking:** Per-run cost logging enables ROI analysis

---

## 20. EOS Usage Patterns

### DM Monitor flow (os-monitor container)
```
Container start → 90-second delay
  → Restore instagram_session.json
  → Navigate to /direct/inbox/
  → Detect unread threads
  → For each unread:
      → Open thread
      → Extract messages
      → AI analysis (model_router)
      → Generate response suggestion
      → Notify founder
  → Sleep interval → repeat
```

### Comment scraping flow (os-scraper container)
```
Cron trigger → apify_scraper.py
  → A/B hashtag rotation
  → Hashtag scraping → Competitor scraping
  → Bot filter → Spam filter → Dedup → Priority classify
  → Save signals to 01_Inbox/raw_signals/
  → Update hashtag performance metrics
  → Weekly: AI hashtag suggestions
  → Log costs
```

### Competitor monitoring
```python
COMPETITOR_ACCOUNTS = [
    "robthebank",     # Similar niche, high engagement
    "imangadzhi",     # Business/hustle content
    "hormozi",        # Business/entrepreneurship
    "noah.rolette",   # Young men's development
    "zackkravits",    # Similar audience
]
```

---

## 21. Gotchas (Real EOS Production Issues)

### /accounts/login/ returns blank page from VPS (ACTIVE)
Instagram detects datacenter IPs and serves blank page for direct login URLs.
**Fix:** Always use root `https://www.instagram.com/`. Login form renders correctly.

### React inputs reject fill() (ACTIVE)
Instagram's React-controlled inputs don't fire onChange with Playwright's `fill()`.
**Fix:** Use `click()` + `type(text, delay=80)` for character-by-character input.

### Cookie-only restore triggers bot detection (RESOLVED)
Using `add_cookies()` instead of `storage_state()` left localStorage missing.
Instagram detected the incomplete session as suspicious.
**Fix:** Always use `storage_state()` for save and restore.

### Chromium SIGBUS in Docker (RESOLVED)
Default Docker `/dev/shm` is 64MB. Chromium needs ~300 MB for rendering.
**Fix:** `shm_size: '2gb'` in docker-compose.yml.

### Startup OOM from rapid restart loops (RESOLVED)
Docker `restart: always` + Chromium 700 MB = RAM exhaustion on rapid restarts.
**Fix:** 90-second `MONITOR_STARTUP_DELAY` + stale session cleanup.

### Mobile UA causes blank page (RESOLVED)
Mobile Safari user agent triggers Instagram's app-redirect page in headless browser.
**Fix:** Desktop Chrome UA renders login form correctly.

### Instagram selector changes (INTERMITTENT)
Instagram updates DOM structure without notice. Thread selectors, message containers,
and unread indicators can break at any time.
**Detection:** Monitor reports 0 threads when unread messages exist.
**Fix:** Update selectors in dm_monitor.py. Use diagnostic screenshots to identify new DOM structure.

### Proxy 403 when RESIDENTIAL credits depleted (ACTIVE)
Apify proxy credits are separate from compute credits.
**Symptom:** All proxy-routed requests return 403 Forbidden.
**Fix:** Set `INSTAGRAM_USE_PROXY=false` or purchase more credits.

### Session expires during overnight monitoring (INTERMITTENT)
Instagram invalidates sessions after 24-72 hours of headless usage.
**Symptom:** DM Monitor redirected to login page.
**Fix:** Monitor detects login redirect and triggers fresh login flow.
Manual intervention needed for verification code relay.
