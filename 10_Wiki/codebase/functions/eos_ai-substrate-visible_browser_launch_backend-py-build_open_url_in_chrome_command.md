---
type: codebase-function
file: eos_ai/substrate/visible_browser_launch_backend.py
line: 77
generated: 2026-05-07
---

# build_open_url_in_chrome_command

**File:** [[eos_ai-substrate-visible_browser_launch_backend-py]] | **Line:** 77
**Signature:** `build_open_url_in_chrome_command(url) → str`

Build the PowerShell command to open a URL in Chrome specifically.

Uses Start-Process with -FilePath pointing to the located chrome.exe.
Does NOT fall back to explorer.exe or default browser.

## Called By

- [[eos_ai-substrate-visible_browser_launch_backend-py-build_drive_open_action]]
- [[eos_ai-substrate-visible_browser_launch_backend-py-execute_chrome_launch]]
