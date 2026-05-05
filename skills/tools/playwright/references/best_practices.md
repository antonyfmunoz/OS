# Playwright — Creator-Level Best Practices
Source: https://playwright.dev/python/
API Version: Playwright 1.58.0
SDK Version: playwright 1.58.0 (pip install playwright)
Last Researched: 2026-04-04

---

# Tier 1 — Technical Mastery

## Authentication

Playwright itself has no authentication. It authenticates TO websites by automating login flows.

### Session persistence via storage_state
```python
# Save (cookies + localStorage)
context.storage_state(path="session.json")

# Restore
context = browser.new_context(storage_state="session.json")
```

Storage state file format:
```json
{
  "cookies": [
    {
      "name": "sessionid",
      "value": "abc123",
      "domain": ".instagram.com",
      "path": "/",
      "expires": 1735689600,
      "httpOnly": true,
      "secure": true,
      "sameSite": "None"
    }
  ],
  "origins": [
    {
      "origin": "https://www.instagram.com",
      "localStorage": [
        {"name": "ig_did", "value": "..."},
        {"name": "csrftoken", "value": "..."}
      ]
    }
  ]
}
```

**Critical:** Both cookies AND localStorage are required for most modern web apps. Cookie-only restoration (via `context.add_cookies()`) misses localStorage state, causing auth failures on sites like Instagram.

### Proxy authentication
```python
browser = p.chromium.launch(proxy={
    'server': 'http://proxy.example.com:8000',
    'username': 'user',
    'password': 'pass',
})
# Or per-context:
context = browser.new_context(proxy={
    'server': 'http://proxy.example.com:8000',
    'username': 'user',
    'password': 'pass',
})
```

### HTTP authentication (Basic/Digest)
```python
context = browser.new_context(http_credentials={
    'username': 'user',
    'password': 'pass',
})
```

## Core Operations with Exact Signatures

### Playwright entry point
```python
# Sync API (used by EOS)
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(**kwargs)
    # ...
# Playwright auto-cleans on context exit

# Async API
from playwright.async_api import async_playwright

async with async_playwright() as playwright:
    browser = await playwright.chromium.launch(**kwargs)
```

### Browser launch
```python
browser = playwright.chromium.launch(
    headless: bool = True,          # headless mode
    args: list[str] = None,         # Chromium flags
    channel: str = None,            # "chrome", "msedge", etc.
    chromium_sandbox: bool = False,  # sandbox (default False in Docker)
    devtools: bool = False,         # auto-open DevTools
    downloads_path: str = None,     # where to save downloads
    executable_path: str = None,    # custom browser binary
    firefox_user_prefs: dict = None,
    handle_sigint: bool = True,     # close on Ctrl+C
    handle_sigterm: bool = True,    # close on SIGTERM
    handle_sighup: bool = True,     # close on SIGHUP
    ignore_default_args: list = None,
    proxy: dict = None,             # {"server": str, "username": str, "password": str, "bypass": str}
    slow_mo: float = None,          # ms delay between operations
    timeout: float = 30000,         # launch timeout ms
    traces_dir: str = None,         # where to save traces
)
# Returns: Browser
```

### Browser context (isolated session)
```python
context = browser.new_context(
    accept_downloads: bool = None,
    base_url: str = None,            # prepended to page.goto() relative URLs
    bypass_csp: bool = None,         # bypass Content-Security-Policy
    color_scheme: str = None,        # "dark" | "light" | "no-preference"
    device_scale_factor: float = None,
    extra_http_headers: dict = None, # additional headers on every request
    geolocation: dict = None,        # {"latitude": float, "longitude": float}
    has_touch: bool = None,
    http_credentials: dict = None,   # {"username": str, "password": str}
    ignore_https_errors: bool = None,
    is_mobile: bool = None,
    java_script_enabled: bool = True,
    locale: str = None,              # e.g., "en-US"
    no_viewport: bool = None,        # disable fixed viewport
    offline: bool = None,            # simulate offline
    permissions: list[str] = None,   # e.g., ["geolocation"]
    proxy: dict = None,              # override browser-level proxy
    record_har_path: str = None,     # record HAR file
    record_video_dir: str = None,    # record video
    record_video_size: dict = None,  # {"width": int, "height": int}
    reduced_motion: str = None,      # "reduce" | "no-preference"
    screen: dict = None,             # {"width": int, "height": int}
    service_workers: str = None,     # "allow" | "block"
    storage_state: str | dict = None,  # path or dict for session restore
    strict_selectors: bool = None,
    timezone_id: str = None,         # e.g., "America/Los_Angeles"
    user_agent: str = None,          # custom UA string
    viewport: dict = None,           # {"width": int, "height": int}
)
# Returns: BrowserContext
```

### Page operations
```python
page = context.new_page()

# Navigation
page.goto(
    url: str,                        # required
    timeout: float = 30000,          # ms
    wait_until: str = "load",        # "load" | "domcontentloaded" | "networkidle" | "commit"
    referer: str = None,
)
# Returns: Response | None

page.reload(timeout=30000, wait_until="load")
page.go_back(timeout=30000, wait_until="load")
page.go_forward(timeout=30000, wait_until="load")

# Properties
page.url         # current URL (str)
page.title()     # page title (str)
page.content()   # full HTML (str)

# Waiting
page.wait_for_selector(
    selector: str,
    state: str = "visible",          # "attached" | "detached" | "visible" | "hidden"
    timeout: float = 30000,
    strict: bool = False,
)
# Returns: ElementHandle | None

page.wait_for_load_state(
    state: str = "load",             # "load" | "domcontentloaded" | "networkidle"
    timeout: float = 30000,
)

page.wait_for_url(
    url: str | Pattern | Callable,
    timeout: float = 30000,
    wait_until: str = "load",
)

page.wait_for_timeout(timeout: float)  # ms — explicit sleep (use sparingly)

# Element queries
page.query_selector(selector: str)           # Returns: ElementHandle | None
page.query_selector_all(selector: str)       # Returns: list[ElementHandle]

# Locator (preferred over query_selector — auto-waits, auto-retries)
page.locator(
    selector: str,
    has: Locator = None,
    has_not: Locator = None,
    has_text: str | Pattern = None,
    has_not_text: str | Pattern = None,
)
# Returns: Locator (lazy — no DOM query until action)

# Screenshots
page.screenshot(
    path: str = None,                # save to file
    type: str = "png",               # "png" | "jpeg"
    quality: int = None,             # jpeg quality 0-100
    full_page: bool = False,         # capture entire scrollable page
    clip: dict = None,               # {"x": float, "y": float, "width": float, "height": float}
    omit_background: bool = False,   # transparent background
    timeout: float = 30000,
    animations: str = None,          # "disabled" | "allow"
    scale: str = None,               # "css" | "device"
)
# Returns: bytes (PNG/JPEG data)

# JavaScript evaluation
page.evaluate(expression: str, arg=None)      # Returns: Any
page.evaluate_handle(expression: str, arg=None)  # Returns: JSHandle

# Keyboard
page.keyboard.press(key: str)                # e.g., "Enter", "Tab", "Escape"
page.keyboard.type(text: str, delay: float = None)  # type text with optional delay per char
page.keyboard.down(key: str)
page.keyboard.up(key: str)
page.keyboard.insert_text(text: str)         # insert without input events

# Close
page.close(run_before_unload: bool = False)
```

### Locator operations (preferred API)
```python
loc = page.locator("css=input[name='email']")

# Actions
loc.click(
    button: str = "left",            # "left" | "right" | "middle"
    click_count: int = 1,
    delay: float = None,             # ms between mousedown and mouseup
    force: bool = False,             # bypass actionability checks
    modifiers: list = None,          # ["Alt", "Control", "Meta", "Shift"]
    no_wait_after: bool = None,
    position: dict = None,           # {"x": float, "y": float}
    timeout: float = 30000,
    trial: bool = False,             # only check actionability, don't click
)

loc.fill(value: str, force=False, no_wait_after=None, timeout=30000)
loc.type(text: str, delay=None, no_wait_after=None, timeout=30000)
loc.press(key: str, delay=None, no_wait_after=None, timeout=30000)
loc.check(force=False, timeout=30000)
loc.uncheck(force=False, timeout=30000)
loc.select_option(value=None, label=None, index=None, timeout=30000)

# State
loc.is_visible(timeout=None)        # Returns: bool
loc.is_hidden(timeout=None)         # Returns: bool
loc.is_enabled(timeout=None)        # Returns: bool
loc.is_disabled(timeout=None)       # Returns: bool
loc.is_checked(timeout=None)        # Returns: bool
loc.is_editable(timeout=None)       # Returns: bool

# Content
loc.inner_text(timeout=30000)       # Returns: str
loc.inner_html(timeout=30000)       # Returns: str
loc.text_content(timeout=30000)     # Returns: str | None
loc.input_value(timeout=30000)      # Returns: str
loc.get_attribute(name: str, timeout=30000)  # Returns: str | None

# Filtering
loc.first                           # Returns: Locator (first match)
loc.last                            # Returns: Locator (last match)
loc.nth(index: int)                 # Returns: Locator (nth match, 0-indexed)
loc.count()                         # Returns: int

# Waiting
loc.wait_for(
    state: str = "visible",          # "attached" | "detached" | "visible" | "hidden"
    timeout: float = 30000,
)
```

### ElementHandle operations (legacy — prefer Locator)
```python
handle = page.query_selector("div.item")

handle.click()
handle.fill("text")
handle.type("text", delay=50)
handle.inner_text()                  # Returns: str
handle.inner_html()                  # Returns: str
handle.text_content()                # Returns: str | None
handle.get_attribute("href")         # Returns: str | None
handle.is_visible()                  # Returns: bool
handle.query_selector("child")       # Returns: ElementHandle | None
handle.query_selector_all("children")  # Returns: list[ElementHandle]
handle.screenshot(path="el.png")
```

## Pagination Patterns

N/A — Playwright is a browser automation tool, not an API with paginated responses.

For scraping paginated web content, implement scrolling or "Load More" clicking:
```python
# Infinite scroll pattern
prev_count = 0
while True:
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)
    items = page.query_selector_all("div.item")
    if len(items) == prev_count:
        break  # no new items loaded
    prev_count = len(items)

# "Load More" button pattern
while True:
    btn = page.locator('button:has-text("Load More")')
    if not btn.is_visible(timeout=3000):
        break
    btn.click()
    page.wait_for_timeout(1000)
```

## Rate Limits

Playwright has no rate limits. Limits come from the target website.

### Instagram-specific limits (observed in EOS)
- Login attempts: ~3-5 per hour before challenge/lockout
- DM inbox navigation: no observed limit, but too-fast navigation triggers bot detection
- Human-like timing is required: `time.sleep(random.uniform(2.0, 3.5))` between actions

### Anti-detection best practices
- Randomize delays between actions: `time.sleep(random.uniform(1.5, 3.5))`
- Use realistic viewport (1280x800, not 1920x1080 which screams "automated")
- Set desktop Chrome UA (mobile UA triggers app redirects)
- Set timezone and locale matching the account's expected location
- Don't navigate faster than a human could

## Error Codes and Recovery

### Playwright exceptions
| Exception | Cause | Recovery |
|-----------|-------|----------|
| `TimeoutError` | Element/page didn't appear within timeout | Increase timeout, check selector validity, check if page loaded |
| `Error: Target page, context or browser has been closed` | Browser/context crashed or was closed | Relaunch browser |
| `Error: net::ERR_CONNECTION_REFUSED` | Target site unreachable | Check network, retry after delay |
| `Error: net::ERR_NAME_NOT_RESOLVED` | DNS failure | Check container networking |
| `Error: Protocol error` | CDP connection to browser lost | Browser crash (OOM), restart |
| `Error: Browser was disconnected` | Chromium process died | Usually OOM or SIGKILL — check `docker logs` |
| `Error: Execution context was destroyed` | Page navigated during JS execution | Re-query elements after navigation |
| `Error: Node is detached from document` | Element removed from DOM between query and action | Re-query the element |
| `Error: Element is not visible` | Element exists but not visible (display:none, offscreen) | Scroll into view, or use `force=True` |

### Chromium crash signals
| Signal | Cause | Recovery |
|--------|-------|----------|
| SIGBUS (7) | /dev/shm too small for Chromium | Set `shm_size: '2gb'` in Docker |
| SIGKILL (9) | OOM killer | Reduce concurrent pages, increase container memory |
| SIGSEGV (11) | Chromium bug or GPU driver issue | Add `--disable-gpu` to launch args |

### EOS error patterns
```python
# Timeout → skip and continue
try:
    page.wait_for_selector('div[dir="auto"]', timeout=15000)
except Exception:
    print("Messages did not load, skipping.")
    page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
    continue

# Session expired → relogin
if "login" in page.url:
    handle_relogin(page, context)
```

## SDK Idioms

### Sync vs Async
Playwright Python has two identical APIs:
- `playwright.sync_api` — blocking calls, simpler code, used by EOS
- `playwright.async_api` — async/await, for use in asyncio event loops

EOS uses sync API because `dm_monitor.py` is a standalone script with its own main loop, not part of an async framework.

### Context manager pattern (required)
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    # ... use browser ...
# Playwright shuts down all browsers on exit
```
The context manager is not optional — it manages the Playwright server subprocess.

### Locator vs ElementHandle
- **Locator** (modern): lazy evaluation, auto-waits, auto-retries, survives DOM changes
- **ElementHandle** (legacy): eager evaluation, no auto-wait, stale if DOM changes

EOS uses both: `query_selector_all` for bulk element enumeration (getting all threads), `locator` for targeted interactions (clicking buttons, filling forms).

### Human-like interaction pattern (EOS standard)
```python
# Click, pause, then type character by character
element.click()
time.sleep(0.5)
element.type(text, delay=80)  # 80ms between keystrokes
time.sleep(random.uniform(1, 2))
```
This bypasses React's synthetic event detection. `fill()` sets the value directly (via JS), which React-controlled inputs may ignore.

### Multi-selector fallback pattern (EOS standard)
```python
selectors = [
    'input[name="email"]',
    'input[autocomplete*="username"]',
    'input[name="username"]',
    'form input[type="text"]',
]
element = None
for sel in selectors:
    try:
        loc = page.locator(sel)
        loc.wait_for(timeout=5000)
        element = loc
        break
    except Exception:
        continue
if not element:
    raise Exception("No matching element found")
```
This handles DOM changes between site versions.

## Anti-Patterns

1. **Using `fill()` on React/Angular inputs** — `fill()` dispatches `input` events that bypass framework change detection. Use `click()` + `type(text, delay=80)` for React-controlled inputs.

2. **Hardcoding selectors for dynamic sites** — Instagram changes its DOM frequently. Use multiple fallback selectors (name, autocomplete, aria-label, type) rather than one specific selector.

3. **Not setting `shm_size` in Docker** — Default 64MB /dev/shm is too small for Chromium. Results in SIGBUS crashes. Always set `shm_size: '2gb'` or use `--disable-dev-shm-usage` flag.

4. **Using `networkidle` wait** — `wait_until="networkidle"` waits for no network requests for 500ms. On SPAs with long-polling or analytics, this either times out or takes forever. Use `domcontentloaded` for most cases.

5. **Not handling stale ElementHandles** — After page navigation or DOM mutation, previously queried ElementHandles become stale. Always re-query after any action that changes the page:
   ```python
   # Wrong
   threads = page.query_selector_all('a[href*="/direct/t/"]')
   threads[0].click()  # navigates
   threads[1].click()  # STALE — DOM has changed
   
   # Right
   threads = page.query_selector_all('a[href*="/direct/t/"]')
   threads[0].click()
   threads = page.query_selector_all('a[href*="/direct/t/"]')  # re-query
   ```

6. **Not closing browser on error** — If the script crashes without `browser.close()`, Chromium processes linger and consume ~700MB each. The `with sync_playwright()` context manager handles this, but any early `return` or unhandled exception INSIDE the with block should still clean up explicitly.

7. **Using `page.wait_for_timeout()` instead of proper waits** — `wait_for_timeout()` is a hard sleep. Prefer `wait_for_selector()` or `wait_for_load_state()` which resolve as soon as the condition is met.

8. **Launching browser per request** — Browser launch takes 1-3 seconds. Create one browser and reuse it across operations. Create new contexts (not browsers) for session isolation.

9. **Mobile UA for desktop-oriented sites** — Some sites (Instagram) redirect mobile UAs to app store pages or serve stripped-down mobile versions. Use desktop Chrome UA for scraping.

10. **Not randomizing delays** — Constant delays (always 2.0s) are a bot fingerprint. Use `random.uniform(1.5, 3.5)` for human-like variance.

## Data Model

### Object hierarchy
```
Playwright (entry point)
├── BrowserType (chromium, firefox, webkit)
│   └── Browser (launched instance)
│       └── BrowserContext (isolated session)
│           ├── cookies + localStorage (storage_state)
│           ├── Page (tab)
│           │   ├── Frame (main + iframes)
│           │   │   ├── Locator (element query)
│           │   │   └── ElementHandle (DOM reference)
│           │   ├── Keyboard
│           │   ├── Mouse
│           │   └── Touchscreen
│           └── Page (another tab)
└── Selectors (custom selector engines)
```

### Lifecycle
- **Playwright** — one per process. Starts Playwright server subprocess.
- **Browser** — one or more per Playwright. Each is a browser process (Chromium/Firefox/WebKit).
- **BrowserContext** — isolated session within a browser. Own cookies, localStorage, cache. Like an incognito window.
- **Page** — a tab within a context. Can have multiple pages per context.
- **Locator** — lazy query. No DOM access until an action is called. Can be chained.
- **ElementHandle** — eager reference to a specific DOM node. Goes stale on DOM changes.

### Selector types
| Prefix | Example | Notes |
|--------|---------|-------|
| `css=` | `css=input[name="email"]` | Default — CSS selector |
| `text=` | `text=Log in` | Text content match |
| `xpath=` | `xpath=//button[@type="submit"]` | XPath |
| `:has-text()` | `button:has-text("Log in")` | CSS + text |
| `>>` | `div.container >> input` | Chained selectors |
| `nth=` | `div.item >> nth=0` | Nth match |

## Webhooks and Events

N/A — Playwright does not have a webhook system. It IS the event consumer, not producer.

### Page events (for monitoring)
```python
# Listen to console messages
page.on("console", lambda msg: print(f"[CONSOLE] {msg.text}"))

# Listen to page errors
page.on("pageerror", lambda err: print(f"[ERROR] {err}"))

# Listen to requests
page.on("request", lambda req: print(f"[REQ] {req.url}"))
page.on("response", lambda resp: print(f"[RESP] {resp.status} {resp.url}"))

# Listen to downloads
page.on("download", lambda dl: print(f"[DOWNLOAD] {dl.url}"))

# Listen to dialogs (alert, confirm, prompt)
page.on("dialog", lambda dialog: dialog.accept())
```

### Network interception
```python
# Block images for faster scraping
def handle_route(route):
    if route.request.resource_type == "image":
        route.abort()
    else:
        route.continue_()

page.route("**/*", handle_route)

# Mock API response
page.route("**/api/data", lambda route: route.fulfill(
    status=200,
    content_type="application/json",
    body='{"data": "mocked"}'
))
```

## Limits

| Resource | Limit |
|----------|-------|
| Concurrent browsers | Limited by RAM (~700MB per Chromium instance) |
| Concurrent pages per browser | No hard limit (practical: 10-50 depending on RAM) |
| Concurrent contexts per browser | No hard limit |
| Selector timeout | Configurable, default 30000ms |
| Navigation timeout | Configurable, default 30000ms |
| File upload size | No Playwright limit (browser/site limit applies) |
| Screenshot size | No limit (full_page=True captures entire scrollable area) |
| `evaluate()` return size | Limited by CDP message size (~100MB) |
| Storage state file | No size limit (practical: <1MB) |

### Memory usage (observed in EOS)
| Component | RAM |
|-----------|-----|
| Chromium process (headless) | ~200-400MB baseline |
| Per-page overhead | ~50-200MB depending on page complexity |
| Instagram DM inbox | ~300-500MB total (Chromium + page) |
| Total os-monitor | ~700MB peak |

## Cost Model

**Free.** Playwright is open source (Apache 2.0 license).

Costs are indirect:
- **RAM** — Chromium is memory-hungry. ~700MB for a single headless instance + one complex page.
- **CPU** — page rendering and JavaScript execution consume CPU during navigation
- **Proxy** — if using residential proxies (Apify: ~$10/GB residential traffic)
- **VPS cost** — os-monitor container needs ~700MB RAM allocation

### EOS proxy costs
- Apify residential proxy: billed by traffic (GB)
- Currently disabled (`INSTAGRAM_USE_PROXY=false`) — VPS has direct Instagram access
- When enabled: ~0.5-2GB/month for DM monitoring (~$5-20/month)

## Version Pinning

### Current versions (EOS Docker image)
- Playwright: **1.58.0** (Python package)
- Chromium: bundled with Playwright (installed via `playwright install chromium --with-deps`)
- Python: 3.11 (from Docker base image)

### In requirements.txt
```
playwright==1.58.0
```

### Browser installation
```bash
# Install Chromium + system dependencies (in Dockerfile)
RUN playwright install chromium --with-deps

# Just Chromium (deps already installed)
RUN playwright install chromium

# All browsers
RUN playwright install --with-deps
```

### Versioning policy
- Playwright releases monthly. Each release bundles specific browser versions.
- Browser versions are NOT independently configurable — they're tied to the Playwright version.
- Breaking changes are rare but happen (selector syntax changes, API renames).
- Pin the Playwright version to avoid surprise browser updates.

### Deprecation warnings
- `query_selector` / `query_selector_all` — not officially deprecated but Locator API is preferred
- `page.fill()` may change behavior for different input types across versions
- `wait_until="networkidle"` — increasingly unreliable as SPAs use persistent connections

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Playwright was built by Microsoft as a successor to Puppeteer (Google's CDP automation library). Key design decisions:

1. **Multi-browser from day one** — Puppeteer was Chrome-only. Playwright supports Chromium, Firefox, and WebKit from the same API. This was the founding differentiator. EOS only uses Chromium but could switch browsers without code changes.

2. **Auto-waiting everywhere** — The Locator API automatically waits for elements to be actionable (visible, enabled, stable) before performing actions. This eliminates most `wait_for_selector()` calls. Puppeteer (and ElementHandle) required manual waits.

3. **Browser contexts as isolation** — Each context is an independent session (cookies, localStorage, cache). This replaces Puppeteer's incognito mode and is more powerful — you can have multiple isolated sessions in one browser process.

4. **Sync + Async dual API** — Python Playwright offers both synchronous and asynchronous APIs with identical functionality. This is unusual — most Python async libraries only offer one. It means Playwright fits both scripts (sync) and web frameworks (async).

5. **Bundled browsers** — Playwright downloads and manages its own browser binaries. You don't install Chrome separately. This ensures the browser version matches the automation protocol version. The tradeoff: Playwright is large (hundreds of MB for browser binaries).

6. **Selector engine extensibility** — Beyond CSS and XPath, Playwright adds text selectors, `:has-text()`, chained selectors (`>>`), and allows registering custom selector engines. This makes targeting elements more expressive.

## Problem-Solution Map and Hidden Capabilities

### "Page loads but elements aren't found"
Cause: Content is dynamically loaded after initial page load. `wait_until="domcontentloaded"` doesn't wait for JS-rendered content.
Fix: Use `page.wait_for_selector("target-element", timeout=60000)` after navigation.

### "Login works locally but fails in Docker"
Cause: Missing `--no-sandbox` flag, or shm_size too small, or network restrictions.
Fix: Launch args `['--no-sandbox', '--disable-dev-shm-usage']` + `shm_size: '2gb'` in Docker.

### "Bot detection despite correct automation"
Cause: Default headless Chrome UA contains `HeadlessChrome`. navigator.webdriver is true.
Fix: Set custom UA via context. For advanced anti-detection:
```python
context = browser.new_context(
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
)
# Hide webdriver flag
page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
""")
```

### "Script works once then fails on repeat"
Cause: Session state wasn't saved, or saved state expired.
Fix: Save `storage_state` after successful login. Check session validity before each run:
```python
page.goto("https://site.com/dashboard")
if "login" in page.url:
    # session expired, relogin
```

### Hidden capabilities
- **Tracing** — record complete browser activity for replay/debugging:
  ```python
  context.tracing.start(screenshots=True, snapshots=True, sources=True)
  # ... actions ...
  context.tracing.stop(path="trace.zip")
  # View: playwright show-trace trace.zip
  ```
- **Video recording** — record page as video:
  ```python
  context = browser.new_context(record_video_dir="videos/")
  # ... actions ...
  page.close()
  path = page.video.path()
  ```
- **HAR recording** — capture all network requests as HAR file:
  ```python
  context = browser.new_context(record_har_path="network.har")
  ```
- **PDF generation** — Chromium-only, headless-only:
  ```python
  page.pdf(path="page.pdf", format="A4", print_background=True)
  ```
- **File download interception**:
  ```python
  with page.expect_download() as dl_info:
      page.click("a.download-link")
  download = dl_info.value
  download.save_as("/path/to/save")
  ```

## Operational Behavior and Edge Cases

### Memory leak with long-running browsers
Chromium's memory usage grows over time with navigation (30+ page loads). Each page load leaves some memory unreclaimable. For long-running scrapers:
- Close and recreate contexts periodically (not the browser — contexts are cheaper)
- Or restart the browser every N iterations
- EOS runs one session per check cycle — less vulnerable but still clears stale sessions weekly

### iframes
Instagram heavily uses iframes for certain features. `page.query_selector()` only searches the main frame. For iframe content:
```python
frame = page.frame(name="iframe_name")
# or
frame = page.frame(url="**/iframe/url/**")
element = frame.query_selector("selector")
```
EOS currently doesn't interact with iframes — DM inbox is in the main frame.

### Shadow DOM
Some modern sites use Shadow DOM (Web Components). Standard selectors don't pierce shadow boundaries. Use:
```python
page.locator("host-element >> shadow=.inner-element")
```

### Navigation race conditions
If a click triggers navigation, subsequent element queries may fail:
```python
# Wrong — click navigates, query fails
page.click("a.link")
page.query_selector("div.new-page")  # may fail if navigation hasn't completed

# Right
page.click("a.link")
page.wait_for_load_state("domcontentloaded")
page.query_selector("div.new-page")
```

### Chromium process zombies
If Python crashes without cleaning up, Chromium processes survive:
```bash
# Find zombie Chromium processes
ps aux | grep chromium | grep -v grep

# Kill all
pkill -f chromium
```
EOS `_clear_stale_chromium_session()` cleans up old session directories but doesn't kill zombie processes. The Docker restart policy handles this — container restart kills all child processes.

## Ecosystem Position and Composition

### Playwright vs Selenium vs Puppeteer
| Feature | Playwright | Selenium | Puppeteer |
|---------|-----------|----------|-----------|
| Browsers | Chromium, Firefox, WebKit | All via WebDriver | Chromium only |
| Protocol | CDP (native) | WebDriver (HTTP) | CDP (native) |
| Auto-wait | Yes (Locator) | No | No |
| Session persist | storage_state | Manual cookies | Manual |
| Language | Python, JS, Java, C# | Many | JS/TS only |
| Speed | Fast (CDP direct) | Slower (HTTP layer) | Fast (CDP direct) |
| Docker | Good (shm_size needed) | Mature | Good |

### Why Playwright for EOS
1. CDP gives direct DOM access — faster than Selenium's WebDriver protocol
2. `storage_state` handles both cookies + localStorage — critical for Instagram
3. Python sync API fits dm_monitor's simple script pattern
4. Built-in browser management — no separate ChromeDriver to maintain

### Complementary tools
- **Apify** — cloud scraping platform. EOS uses Apify for proxy and for comment scraping (separate from Playwright). Could replace Playwright for simpler scraping tasks.
- **requests/httpx** — for API calls that don't need browser rendering. Don't use Playwright when a simple HTTP request works.
- **BeautifulSoup** — for parsing HTML that's already fetched. Can pair with Playwright's `page.content()`.

## Trajectory and Evolution

### Recent changes (2025-2026)
- Locator API stabilized as primary element interaction pattern
- `page.clock` API for time manipulation in tests
- Improved Docker support and documentation
- Better network interception patterns
- Custom fixture support for pytest integration
- Component testing for React, Vue, Svelte

### Direction
- **Test-first focus** — Playwright is increasingly positioned as a testing tool, not a scraping tool. Features favor test scenarios.
- **Component testing** — direct rendering and testing of framework components
- **AI integration** — code generation from natural language test descriptions
- **Performance** — faster browser startup, reduced memory footprint

### Deprecation risks
- `query_selector` / `query_selector_all` may eventually be deprecated in favor of Locator
- `page.$(selector)` shorthand may be removed
- Browser compatibility: Playwright tracks browser releases — old Playwright versions may not work with new browser features

## Conceptual Model and Solution Recipes

### Mental model
Think of Playwright as **a human controlling a browser programmatically**:
1. **Launch** — open the browser application
2. **Context** — open an incognito window (isolated session)
3. **Navigate** — type a URL and press Enter
4. **Wait** — watch the page until it's ready
5. **Interact** — click buttons, fill forms, read text
6. **Persist** — save cookies/session for next time

### Recipe: Instagram DM check (EOS standard flow)
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
    
    # Restore session or fresh login
    if os.path.exists("session.json"):
        context = browser.new_context(storage_state="session.json", user_agent=UA, viewport=VP)
    else:
        context = browser.new_context(user_agent=UA, viewport=VP)
    
    page = context.new_page()
    page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
    
    if "login" in page.url:
        do_login(page, context)  # fills form, handles challenges
    
    page.wait_for_selector("div[role='main']", timeout=60000)
    threads = page.query_selector_all('a[href*="/direct/t/"]')
    
    for thread in threads:
        thread.click()
        time.sleep(random.uniform(2, 3.5))
        messages = page.query_selector_all('div[dir="auto"]')
        # ... process messages ...
        page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
    
    context.storage_state(path="session.json")
    browser.close()
```

### Recipe: Diagnostic screenshot on failure
```python
try:
    page.wait_for_selector("expected-element", timeout=15000)
except Exception:
    os.makedirs('/opt/OS/logs', exist_ok=True)
    page.screenshot(path=f'/opt/OS/logs/failure_{datetime.now().isoformat()}.png')
    print(f"Screenshot saved. Current URL: {page.url}")
    raise
```

### Recipe: Safe login with verification code relay
```python
# Fill credentials
page.locator('input[name="email"]').click()
page.locator('input[name="email"]').type(username, delay=80)
page.locator('input[name="pass"]').click()
page.locator('input[name="pass"]').type(password, delay=80)
page.keyboard.press("Enter")
time.sleep(random.uniform(3, 5))

# Check for verification challenge
if any(kw in page.url for kw in ["codeentry", "challenge", "checkpoint"]):
    send_telegram("Verification code needed!")
    code = wait_for_code(timeout=600)
    page.locator('input[name="verificationCode"]').type(code, delay=120)
    page.keyboard.press("Enter")
```

## Industry Expert and Cutting-Edge Usage

### Pattern: Session rotation for anti-detection
Rotate between multiple saved sessions (different accounts or different browser fingerprints):
```python
sessions = glob.glob("sessions/*.json")
session = random.choice(sessions)
context = browser.new_context(storage_state=session)
```

### Pattern: Visual regression with screenshots
Take screenshots at key states and compare:
```python
page.screenshot(path=f"snapshots/{step_name}.png")
# Compare with previous run using image diff tools
```

### Pattern: Network interception for speed
Block heavy resources that aren't needed for scraping:
```python
def block_heavy_resources(route):
    if route.request.resource_type in ("image", "stylesheet", "font", "media"):
        route.abort()
    else:
        route.continue_()

page.route("**/*", block_heavy_resources)
```
This can reduce page load time by 50-70% and memory usage significantly.

### Pattern: Parallel scraping with multiple contexts
```python
contexts = [browser.new_context() for _ in range(3)]
pages = [ctx.new_page() for ctx in contexts]
# Use threading or asyncio to drive pages in parallel
```
Each context is isolated — separate cookies, separate sessions. Share one browser process.

### Pattern: Stealth mode configuration
```python
context = browser.new_context(
    user_agent="realistic desktop UA",
    viewport={"width": 1280, "height": 800},
    locale="en-US",
    timezone_id="America/Los_Angeles",
    color_scheme="light",
)
page = context.new_page()
page.add_init_script("""
    // Hide automation indicators
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    window.chrome = {runtime: {}};
""")
```

---

## EOS Usage Patterns

### Service: os-monitor (dm_monitor.py)
- Sync API (`sync_playwright`)
- Single Chromium instance, single context, single page
- Headless mode with desktop Chrome UA
- Session persistence via `instagram_session.json`
- 90-second startup delay to prevent restart-loop OOM
- Stale session cleanup every 7 days (`_clear_stale_chromium_session`)
- Human-like delays: `random.uniform(1.5, 3.5)` between actions
- Character-by-character typing: `delay=80` for inputs, `delay=120` for verification codes

### Docker configuration
```yaml
# docker-compose.yml (os-monitor)
shm_size: '2gb'           # Chromium needs large /dev/shm
environment:
  - PYTHONUNBUFFERED=1     # stream Playwright logs
```

### Launch arguments
```python
browser = p.chromium.launch(
    headless=True,
    args=['--no-sandbox', '--disable-dev-shm-usage'],
)
```

### Session management flow
```
Startup → check instagram_session.json exists?
  → Yes: restore via storage_state → validate (navigate to inbox)
    → Valid: proceed
    → Invalid: delete file → fresh login
  → No: fresh login
    → Fill credentials → handle challenges → save storage_state
```

### Proxy configuration (optional)
```python
# Enabled via INSTAGRAM_USE_PROXY=true
# Uses Apify residential proxy with sticky sessions
proxy = {
    'server': 'http://proxy.apify.com:8000',
    'username': f'groups-RESIDENTIAL,session-{sticky_id},country-US',
    'password': os.getenv('APIFY_PROXY_PASSWORD'),
}
```

## Gotchas

### Chromium SIGBUS in Docker (RESOLVED)
Default `/dev/shm` is 64MB. Chromium uses shared memory for compositing and rendering. Complex pages (Instagram) exceed 64MB instantly. Container crashes with signal 7 (SIGBUS). Fixed: `shm_size: '2gb'` in compose.yml.

### Instagram login URL blank page (ACTIVE)
`https://www.instagram.com/accounts/login/` returns a blank page from VPS IPs. Instagram redirects automated-looking requests to an empty page. Navigate to `https://www.instagram.com/` instead — the root URL serves the login form within the main app shell.

### React `fill()` vs `type()` (ACTIVE)
Instagram uses React with controlled inputs. `fill()` sets the value via JavaScript but doesn't trigger React's `onChange` handler properly. `type()` with `delay=80` simulates real keystrokes that React detects. Always use `click()` + `type()` for React forms.

### Startup OOM from rapid restart loops (RESOLVED)
`restart: always` + crash → restart → crash → restart. Each restart spawns a new Chromium (~700MB). Three restarts = 2.1GB just in Chromium processes. Fixed with `MONITOR_STARTUP_DELAY=90` seconds.

### Mobile UA app redirect (RESOLVED)
Mobile Safari UA causes Instagram to serve a deep-link redirect (opens app store). Headless Chromium can't handle app deep links. Desktop Chrome UA renders the standard web app correctly.

### DOM selector changes between Instagram versions (ONGOING)
Instagram updates its DOM structure without notice. Selectors that worked last week may fail. EOS handles this with multi-selector fallback arrays (`_username_selectors`, `_code_selectors`) that try multiple options.

### WebFetch fails on Playwright docs (NOTED)
Playwright's documentation site (playwright.dev) uses heavy JS rendering that WebFetch times out on. Use WebSearch for doc lookups instead of WebFetch.
