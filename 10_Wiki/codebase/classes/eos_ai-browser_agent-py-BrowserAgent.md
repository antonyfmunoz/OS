---
type: codebase-class
file: eos_ai/browser_agent.py
line: 36
generated: 2026-04-11
---

# BrowserAgent

**File:** [[eos_ai-browser_agent-py]] | **Line:** 36

*No docstring.*

## Inherited By

- [[eos_ai-browser_agent-py-ManusAgent]]
- [[eos_ai-browser_agent-py-InstagramAgent]]

## Methods

- [[eos_ai-browser_agent-py-BrowserAgent-__init__]]`(headless) → None` — 
- [[eos_ai-browser_agent-py-BrowserAgent-start]]`() → None` — 
- [[eos_ai-browser_agent-py-BrowserAgent-stop]]`() → None` — 
- [[eos_ai-browser_agent-py-BrowserAgent-navigate]]`(url) → str` — Navigate to URL. Returns final URL after redirects.
- [[eos_ai-browser_agent-py-BrowserAgent-get_text]]`(selector, timeout) → str` — Get inner text of a specific element. Returns '' on miss.
- [[eos_ai-browser_agent-py-BrowserAgent-get_page_text]]`() → str` — Get full visible text of the page body.
- [[eos_ai-browser_agent-py-BrowserAgent-get_all_inputs]]`() → list[dict]` — Return all input/textarea/select fields with their attributes.
- [[eos_ai-browser_agent-py-BrowserAgent-extract_table]]`(selector) → list[dict]` — Extract table data as a list of row dicts keyed by column headers.
- [[eos_ai-browser_agent-py-BrowserAgent-click]]`(selector, timeout) → bool` — Click an element. Returns True on success, False on miss.
- [[eos_ai-browser_agent-py-BrowserAgent-type_into]]`(selector, text, delay, timeout) → bool` — Click then type into a field. Returns True on success.
- [[eos_ai-browser_agent-py-BrowserAgent-select_option]]`(selector, value) → bool` — Select a dropdown option by value. Returns True on success.
- [[eos_ai-browser_agent-py-BrowserAgent-wait_for]]`(selector, timeout) → bool` — Wait for element to appear. Returns True when found.
- [[eos_ai-browser_agent-py-BrowserAgent-fill_form]]`(fields, submit_selector, delay) → dict` — Fill multiple form fields at once.
- [[eos_ai-browser_agent-py-BrowserAgent-screenshot]]`(path) → bool` — Save screenshot to path. Returns True on success.
- [[eos_ai-browser_agent-py-BrowserAgent-extract_page_state]]`() → dict` — Extract full structured state of the current page.
- [[eos_ai-browser_agent-py-BrowserAgent-run_task]]`(task_description, ctx) → dict` — Higher-level: describe what to do, agent reasons about how.
