---
type: codebase-function
file: eos_ai/substrate/visible_browser_launch_backend.py
line: 257
generated: 2026-05-07
---

# execute_browser_launch

**File:** [[eos_ai-substrate-visible_browser_launch_backend-py]] | **Line:** 257
**Signature:** `execute_browser_launch(url) → dict[str, Any]`

Execute a visible browser launch — CHROME PREFERRED.

Tries Chrome first. If Chrome is not found, returns BACKEND_MISSING
instead of silently falling back to Explorer/default browser.

## Calls

- [[eos_ai-substrate-visible_browser_launch_backend-py-execute_chrome_launch]]
