---
type: codebase-function
file: eos_ai/browser_agent.py
line: 192
generated: 2026-04-12
---

# BrowserAgent.fill_form

**File:** [[eos_ai-browser_agent-py]] | **Line:** 192
**Signature:** `fill_form(fields, submit_selector, delay) → dict`

**Class:** [[eos_ai-browser_agent-py-BrowserAgent]]

Fill multiple form fields at once.
fields: {selector: value}
Returns {filled: int, failed: list[str]}

## Calls

- [[eos_ai-browser_agent-py-BrowserAgent-click]]
- [[eos_ai-browser_agent-py-BrowserAgent-type_into]]

## Called By

- [[eos_ai-browser_agent-py-InstagramAgent-login]]
