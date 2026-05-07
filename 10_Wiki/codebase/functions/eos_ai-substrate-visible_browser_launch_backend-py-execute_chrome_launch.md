---
type: codebase-function
file: eos_ai/substrate/visible_browser_launch_backend.py
line: 189
generated: 2026-05-07
---

# execute_chrome_launch

**File:** [[eos_ai-substrate-visible_browser_launch_backend-py]] | **Line:** 189
**Signature:** `execute_chrome_launch(url) → dict[str, Any]`

Execute a Chrome-specific browser launch. Returns result dict.

Uses the PowerShell command that locates chrome.exe and launches it.
Does NOT fall back to Explorer/default browser on failure.

## Calls

- [[eos_ai-substrate-visible_browser_launch_backend-py-build_backend_missing_message]]
- [[eos_ai-substrate-visible_browser_launch_backend-py-build_open_url_in_chrome_command]]
- [[eos_ai-substrate-visible_browser_launch_backend-py-validate_url_allowed]]

## Called By

- [[eos_ai-substrate-visible_browser_launch_backend-py-execute_browser_launch]]
