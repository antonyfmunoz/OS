---
type: codebase-function
file: eos_ai/substrate/chrome_accessibility_launch_backend.py
line: 67
generated: 2026-05-07
---

# build_chrome_accessibility_launch_command

**File:** [[eos_ai-substrate-chrome_accessibility_launch_backend-py]] | **Line:** 67
**Signature:** `build_chrome_accessibility_launch_command(chrome_path, profile_directory, url) → str`

Build Chrome launch command with accessibility flag.

Includes --force-renderer-accessibility so UIAutomation can read
the web page content (file list, navigation, buttons).
