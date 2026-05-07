---
type: codebase-function
file: eos_ai/substrate/visible_browser_launch_backend.py
line: 167
generated: 2026-05-07
---

# build_backend_missing_message

**File:** [[eos_ai-substrate-visible_browser_launch_backend-py]] | **Line:** 167
**Signature:** `build_backend_missing_message(reason) → dict[str, Any]`

Build a BACKEND_MISSING message when Chrome cannot be found.

Does NOT silently fall back to Explorer/default browser.
Asks advisor for decision.

## Called By

- [[eos_ai-substrate-visible_browser_launch_backend-py-execute_chrome_launch]]
