---
type: codebase-function
file: eos_ai/substrate/chrome_profile_launch_backend.py
line: 98
generated: 2026-05-07
---

# build_chrome_profile_drive_launch_command

**File:** [[eos_ai-substrate-chrome_profile_launch_backend-py]] | **Line:** 98
**Signature:** `build_chrome_profile_drive_launch_command(chrome_path, profile_directory, url) → str`

Build the Chrome launch command with --profile-directory flag.

This opens Chrome with the specified profile directly.
No account switching UI. No credential entry.
