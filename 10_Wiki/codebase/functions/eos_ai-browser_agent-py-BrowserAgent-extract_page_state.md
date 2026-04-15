---
type: codebase-function
file: eos_ai/browser_agent.py
line: 227
generated: 2026-04-12
---

# BrowserAgent.extract_page_state

**File:** [[eos_ai-browser_agent-py]] | **Line:** 227
**Signature:** `extract_page_state() → dict`

**Class:** [[eos_ai-browser_agent-py-BrowserAgent]]

Extract full structured state of the current page.
Returns title, url, headings, links, inputs, and truncated body text.
Used after every navigation — not screenshots.

## Calls

- [[eos_ai-browser_agent-py-BrowserAgent-get_all_inputs]]

## Called By

- [[eos_ai-browser_agent-py-BrowserAgent-run_task]]
