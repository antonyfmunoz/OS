---
type: codebase-function
file: eos_ai/substrate/chrome_profile_launch_backend.py
line: 144
generated: 2026-05-07
---

# build_ssh_profile_launch_sequence

**File:** [[eos_ai-substrate-chrome_profile_launch_backend-py]] | **Line:** 144
**Signature:** `build_ssh_profile_launch_sequence(profile_directory) → list[str]`

Build the full SSH command sequence for profile-specific Chrome launch.

Returns list of SSH commands to execute in order:
1. Create scheduled task
2. Run scheduled task
...

## Calls

- [[eos_ai-substrate-chrome_profile_launch_backend-py-build_task_scheduler_profile_launch]]
