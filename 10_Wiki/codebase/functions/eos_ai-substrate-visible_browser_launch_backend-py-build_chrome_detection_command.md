---
type: codebase-function
file: eos_ai/substrate/visible_browser_launch_backend.py
line: 58
generated: 2026-05-07
---

# build_chrome_detection_command

**File:** [[eos_ai-substrate-visible_browser_launch_backend-py]] | **Line:** 58
**Signature:** `build_chrome_detection_command() → str`

Build a PowerShell command that finds Chrome on Windows.

Returns the PowerShell command string that tests each candidate path
and returns the first existing one, or throws if Chrome is not found.
