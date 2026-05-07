---
type: codebase-function
file: eos_ai/substrate/chrome_profile_launch_backend.py
line: 51
generated: 2026-05-07
---

# validate_profile_directory

**File:** [[eos_ai-substrate-chrome_profile_launch_backend-py]] | **Line:** 51
**Signature:** `validate_profile_directory(profile_directory) → list[str]`

Validate that a profile directory name is safe.

Must be: 'Default', 'Profile 1', 'Profile 2', etc.
Blocks path traversal and injection.
