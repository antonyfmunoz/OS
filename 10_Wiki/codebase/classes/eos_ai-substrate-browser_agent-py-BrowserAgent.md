---
type: codebase-class
file: eos_ai/substrate/browser_agent.py
line: 159
generated: 2026-05-07
---

# BrowserAgent

**File:** [[eos_ai-substrate-browser_agent-py]] | **Line:** 159

Singleton browser execution surface backed by Playwright headless Chromium.

Thread-safe. Lazy init on first use. One browser / context / page at a time.

## Inherited By

- [[eos_ai-browser_agent-py-ManusAgent]]
- [[eos_ai-browser_agent-py-InstagramAgent]]

## Methods

- [[eos_ai-substrate-browser_agent-py-BrowserAgent-__init__]]`() → None` — 
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-default]]`() → BrowserAgent` — Return the process-wide singleton, creating on first call.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-reset_default_for_tests]]`() → None` — Tear down the singleton. Next default() creates a fresh instance.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_ensure_browser]]`() → None` — Lazily start Playwright + headless Chromium. Caller holds _lock.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_ensure_page]]`() → None` — Create a page if one does not exist. Caller holds _lock.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-close]]`() → None` — Tear down all resources: page, context, browser, playwright.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-execute]]`(action, payload) → BrowserActionResult` — Thread-safe dispatch to the appropriate action handler.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_dispatch]]`(action, payload) → BrowserActionResult` — Route to the correct handler. Caller holds _lock.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_has_page]]`() → bool` — Return True if there is an active, non-closed page.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_no_page_error]]`(action) → BrowserActionResult` — Return a standard error for actions that require an active page.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_do_open_url]]`(payload) → BrowserActionResult` — Navigate to a URL. Creates a page if needed.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_do_click]]`(payload) → BrowserActionResult` — Click an element by CSS selector.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_do_type_text]]`(payload) → BrowserActionResult` — Fill a text field by CSS selector.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_do_extract]]`(payload) → BrowserActionResult` — Extract text content from an element by CSS selector.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_do_screenshot]]`(payload) → BrowserActionResult` — Take a full-page screenshot. Optional 'path' in payload.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_do_navigate_back]]`(payload) → BrowserActionResult` — Go back in browser history.
- [[eos_ai-substrate-browser_agent-py-BrowserAgent-_do_close]]`() → BrowserActionResult` — Close the browser and all resources.
