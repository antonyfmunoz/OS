---
type: codebase-class
file: eos_ai/browser_agent.py
line: 478
generated: 2026-05-07
---

# InstagramAgent

**File:** [[eos_ai-browser_agent-py]] | **Line:** 478

Control Instagram via browser for DM sending without the API.

Requires INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD in .env.
Session is maintained across calls within the same agent instance.

## Inherits From

- [[eos_ai-substrate-browser_agent-py-BrowserAgent]]

## Methods

- [[eos_ai-browser_agent-py-InstagramAgent-login]]`() → bool` — Log in using env credentials. Returns True on success.
- [[eos_ai-browser_agent-py-InstagramAgent-send_dm]]`(username, message) → dict` — Send a DM to @username.
