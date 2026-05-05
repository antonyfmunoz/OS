<<<<<<< Updated upstream
---
name: playwright
description: "Use when any agent needs browser automation, web scraping, DOM interaction, session management, or headless Chromium operations."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://playwright.dev/python/"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "Playwright 1.58.0"
sdk_version: "playwright 1.58.0 (Python, sync API)"
speed_category: "stable"
trigger: both
effort: low
context: fork
---

# Tool: Playwright

## What This Tool Does

Playwright is a browser automation library by Microsoft that controls Chromium, Firefox, and WebKit via the Chrome DevTools Protocol (CDP). It provides a Python API for headless and headed browser operations: navigation, DOM interaction, form filling, screenshots, session persistence, and network interception.

Core capabilities:
- **Browser lifecycle** — launch, create contexts (isolated sessions), create pages (tabs)
- **Navigation** — `goto()` with configurable wait conditions (domcontentloaded, load, networkidle)
- **DOM interaction** — selectors (`locator`, `query_selector`, `query_selector_all`), click, fill, type, press
- **Session persistence** — `storage_state()` saves/restores cookies + localStorage as JSON
- **Screenshots** — full page or element-level, PNG or JPEG
- **JavaScript evaluation** — `evaluate()` runs arbitrary JS in page context
- **Network** — request interception, response monitoring, proxy support
- **Waiting** — `wait_for_selector`, `wait_for_load_state`, `wait_for_url`, configurable timeouts

## EOS Integration

**Primary use:** Instagram DM monitoring via `services/dm_monitor.py` (os-monitor container).

**What it does:**
1. Launches headless Chromium inside Docker
2. Logs into Instagram using stored session (storage_state) or fresh credentials
3. Navigates to DM inbox, detects unread threads
4. Extracts messages via DOM selectors
5. Feeds extracted messages to AI for sales conversation assistance
6. Takes diagnostic screenshots on failures

**Architecture:**
```
os-monitor container
  └── dm_monitor.py
        └── sync_playwright()
              └── chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
                    └── browser.new_context(storage_state=..., user_agent=..., viewport=...)
                          └── context.new_page()
                                ├── page.goto("instagram.com/direct/inbox/")
                                ├── page.query_selector_all('a[href*="/direct/t/"]')
                                ├── page.locator('input[name="email"]').type(...)
                                └── context.storage_state(path=...)
```

**Docker config:**
- `shm_size: '2gb'` — Chromium uses /dev/shm for rendering; default 64MB causes SIGBUS crashes
- `PYTHONUNBUFFERED=1` — streams Playwright logs to `docker logs`
- `--no-sandbox` — required inside Docker (container is already sandboxed)
- `--disable-dev-shm-usage` — forces Chromium to use /tmp instead of /dev/shm as fallback

**Agents that use it:** DM Monitor (directly), EA Agent (indirectly via DM Monitor reports)

## Authentication

Playwright itself requires no authentication. It authenticates TO target sites on behalf of EOS.

### Instagram auth flow
1. Check for saved `instagram_session.json` (storage_state)
2. If exists → `browser.new_context(storage_state=path)` → validate by navigating to inbox
3. If invalid → fresh login:
   - Navigate to `https://www.instagram.com/` (not `/accounts/login/` — blank page from VPS IPs)
   - Fill username via `input[name="email"]` (not "username" — Instagram changed the DOM)
   - Fill password via `input[name="pass"]`
   - Handle verification code challenges via Telegram relay
   - Dismiss prompts ("Save Info", "Not Now")
   - Save session: `context.storage_state(path=instagram_session.json)`

### Session file format
```json
{
  "cookies": [...],
  "origins": [
    {
      "origin": "https://www.instagram.com",
      "localStorage": [{"name": "key", "value": "value"}, ...]
    }
  ]
}
```
Both cookies AND localStorage are required. Cookie-only restore triggers Instagram bot detection.

### Environment variables
| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Login email/username |
| `INSTAGRAM_PASSWORD` | Login password |
| `INSTAGRAM_USE_PROXY` | `true` to use Apify residential proxy |
| `APIFY_PROXY_PASSWORD` | Proxy auth (when proxy enabled) |

## Quick Reference

### Launch pattern (EOS standard)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'],
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
        viewport={'width': 1280, 'height': 800},
        locale='en-US',
        timezone_id='America/Los_Angeles',
    )
    page = context.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded")
```

### Session restore
```python
# Save
context.storage_state(path="session.json")

# Restore
context = browser.new_context(storage_state="session.json")
```

### Element interaction
```python
# Locator (preferred — auto-waits, auto-retries)
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type("text", delay=80)
page.locator('button:has-text("Log in")').click()

# Query selector (legacy — returns ElementHandle or None)
el = page.query_selector('div[dir="auto"]')
elements = page.query_selector_all('a[href*="/direct/t/"]')

# JavaScript evaluation
inputs = page.evaluate("""() => {
    return Array.from(document.querySelectorAll('input')).map(i => ({
        name: i.name, type: i.type
    }));
}""")
```

### Waiting
```python
page.wait_for_selector("div[role='main']", timeout=60000)
page.wait_for_load_state("domcontentloaded")
page.wait_for_url("**/inbox/**")
```

### Screenshots
```python
page.screenshot(path="/opt/OS/logs/screenshot.png")
page.screenshot(path="full.png", full_page=True)
element.screenshot(path="element.png")
```

### Proxy (EOS Apify residential proxy)
```python
browser = p.chromium.launch(
    headless=True,
    args=['--no-sandbox'],
    proxy={
        'server': 'http://proxy.apify.com:8000',
        'username': f'groups-RESIDENTIAL,session-{sticky_id},country-US',
        'password': apify_pass,
    },
)
```

## Gotchas

### Chromium SIGBUS in Docker (RESOLVED)
Default Docker `/dev/shm` is 64MB. Chromium uses shared memory for rendering — exceeding it causes SIGBUS (signal 7). Fixed with `shm_size: '2gb'` in docker-compose.yml.

### Instagram `/accounts/login/` returns blank page (ACTIVE)
Direct login URL returns a blank page from VPS IPs (bot detection). Navigate to `https://www.instagram.com/` instead — the login form renders correctly there.

### Cookie-only session restore triggers bot detection (RESOLVED)
Instagram auth lives in both cookies AND localStorage. Using only `context.add_cookies()` left sessions incomplete. Fixed by using `storage_state()` which saves both.

### React inputs reject `fill()` (ACTIVE)
Instagram's React-controlled inputs reject synthetic `fill()` events. Must use `click()` + `type(text, delay=80)` to simulate character-by-character typing that React's onChange handler captures.

### Startup OOM from rapid restart loops (RESOLVED)
Docker `restart: always` caused rapid Chromium restarts (~700MB each), exhausting RAM. Fixed with 90-second startup delay (`MONITOR_STARTUP_DELAY=90`) and `_clear_stale_chromium_session()` to clean up old user-data dirs.

### Mobile User-Agent causes blank page (RESOLVED)
Mobile Safari UA causes Instagram to serve an app-redirect blank page in headless Chromium. Desktop Chrome UA confirmed to render login form correctly.

See references/best_practices.md for full API reference, anti-patterns, and advanced patterns.
=======
---
name: playwright
description: "Use when any agent needs browser automation, web scraping, DOM interaction, session management, or headless Chromium operations."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://playwright.dev/python/"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "Playwright 1.58.0"
sdk_version: "playwright 1.58.0 (Python, sync API)"
speed_category: "stable"
---

# Tool: Playwright

## What This Tool Does

Playwright is a browser automation library by Microsoft that controls Chromium, Firefox, and WebKit via the Chrome DevTools Protocol (CDP). It provides a Python API for headless and headed browser operations: navigation, DOM interaction, form filling, screenshots, session persistence, and network interception.

Core capabilities:
- **Browser lifecycle** — launch, create contexts (isolated sessions), create pages (tabs)
- **Navigation** — `goto()` with configurable wait conditions (domcontentloaded, load, networkidle)
- **DOM interaction** — selectors (`locator`, `query_selector`, `query_selector_all`), click, fill, type, press
- **Session persistence** — `storage_state()` saves/restores cookies + localStorage as JSON
- **Screenshots** — full page or element-level, PNG or JPEG
- **JavaScript evaluation** — `evaluate()` runs arbitrary JS in page context
- **Network** — request interception, response monitoring, proxy support
- **Waiting** — `wait_for_selector`, `wait_for_load_state`, `wait_for_url`, configurable timeouts

## EOS Integration

**Primary use:** Instagram DM monitoring via `services/dm_monitor.py` (os-monitor container).

**What it does:**
1. Launches headless Chromium inside Docker
2. Logs into Instagram using stored session (storage_state) or fresh credentials
3. Navigates to DM inbox, detects unread threads
4. Extracts messages via DOM selectors
5. Feeds extracted messages to AI for sales conversation assistance
6. Takes diagnostic screenshots on failures

**Architecture:**
```
os-monitor container
  └── dm_monitor.py
        └── sync_playwright()
              └── chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
                    └── browser.new_context(storage_state=..., user_agent=..., viewport=...)
                          └── context.new_page()
                                ├── page.goto("instagram.com/direct/inbox/")
                                ├── page.query_selector_all('a[href*="/direct/t/"]')
                                ├── page.locator('input[name="email"]').type(...)
                                └── context.storage_state(path=...)
```

**Docker config:**
- `shm_size: '2gb'` — Chromium uses /dev/shm for rendering; default 64MB causes SIGBUS crashes
- `PYTHONUNBUFFERED=1` — streams Playwright logs to `docker logs`
- `--no-sandbox` — required inside Docker (container is already sandboxed)
- `--disable-dev-shm-usage` — forces Chromium to use /tmp instead of /dev/shm as fallback

**Agents that use it:** DM Monitor (directly), EA Agent (indirectly via DM Monitor reports)

## Authentication

Playwright itself requires no authentication. It authenticates TO target sites on behalf of EOS.

### Instagram auth flow
1. Check for saved `instagram_session.json` (storage_state)
2. If exists → `browser.new_context(storage_state=path)` → validate by navigating to inbox
3. If invalid → fresh login:
   - Navigate to `https://www.instagram.com/` (not `/accounts/login/` — blank page from VPS IPs)
   - Fill username via `input[name="email"]` (not "username" — Instagram changed the DOM)
   - Fill password via `input[name="pass"]`
   - Handle verification code challenges via Telegram relay
   - Dismiss prompts ("Save Info", "Not Now")
   - Save session: `context.storage_state(path=instagram_session.json)`

### Session file format
```json
{
  "cookies": [...],
  "origins": [
    {
      "origin": "https://www.instagram.com",
      "localStorage": [{"name": "key", "value": "value"}, ...]
    }
  ]
}
```
Both cookies AND localStorage are required. Cookie-only restore triggers Instagram bot detection.

### Environment variables
| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_USERNAME` | Login email/username |
| `INSTAGRAM_PASSWORD` | Login password |
| `INSTAGRAM_USE_PROXY` | `true` to use Apify residential proxy |
| `APIFY_PROXY_PASSWORD` | Proxy auth (when proxy enabled) |

## Quick Reference

### Launch pattern (EOS standard)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage'],
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
        viewport={'width': 1280, 'height': 800},
        locale='en-US',
        timezone_id='America/Los_Angeles',
    )
    page = context.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded")
```

### Session restore
```python
# Save
context.storage_state(path="session.json")

# Restore
context = browser.new_context(storage_state="session.json")
```

### Element interaction
```python
# Locator (preferred — auto-waits, auto-retries)
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type("text", delay=80)
page.locator('button:has-text("Log in")').click()

# Query selector (legacy — returns ElementHandle or None)
el = page.query_selector('div[dir="auto"]')
elements = page.query_selector_all('a[href*="/direct/t/"]')

# JavaScript evaluation
inputs = page.evaluate("""() => {
    return Array.from(document.querySelectorAll('input')).map(i => ({
        name: i.name, type: i.type
    }));
}""")
```

### Waiting
```python
page.wait_for_selector("div[role='main']", timeout=60000)
page.wait_for_load_state("domcontentloaded")
page.wait_for_url("**/inbox/**")
```

### Screenshots
```python
page.screenshot(path="/opt/OS/logs/screenshot.png")
page.screenshot(path="full.png", full_page=True)
element.screenshot(path="element.png")
```

### Proxy (EOS Apify residential proxy)
```python
browser = p.chromium.launch(
    headless=True,
    args=['--no-sandbox'],
    proxy={
        'server': 'http://proxy.apify.com:8000',
        'username': f'groups-RESIDENTIAL,session-{sticky_id},country-US',
        'password': apify_pass,
    },
)
```

## Gotchas

### Chromium SIGBUS in Docker (RESOLVED)
Default Docker `/dev/shm` is 64MB. Chromium uses shared memory for rendering — exceeding it causes SIGBUS (signal 7). Fixed with `shm_size: '2gb'` in docker-compose.yml.

### Instagram `/accounts/login/` returns blank page (ACTIVE)
Direct login URL returns a blank page from VPS IPs (bot detection). Navigate to `https://www.instagram.com/` instead — the login form renders correctly there.

### Cookie-only session restore triggers bot detection (RESOLVED)
Instagram auth lives in both cookies AND localStorage. Using only `context.add_cookies()` left sessions incomplete. Fixed by using `storage_state()` which saves both.

### React inputs reject `fill()` (ACTIVE)
Instagram's React-controlled inputs reject synthetic `fill()` events. Must use `click()` + `type(text, delay=80)` to simulate character-by-character typing that React's onChange handler captures.

### Startup OOM from rapid restart loops (RESOLVED)
Docker `restart: always` caused rapid Chromium restarts (~700MB each), exhausting RAM. Fixed with 90-second startup delay (`MONITOR_STARTUP_DELAY=90`) and `_clear_stale_chromium_session()` to clean up old user-data dirs.

### Mobile User-Agent causes blank page (RESOLVED)
Mobile Safari UA causes Instagram to serve an app-redirect blank page in headless Chromium. Desktop Chrome UA confirmed to render login form correctly.

See references/best_practices.md for full API reference, anti-patterns, and advanced patterns.
>>>>>>> Stashed changes
