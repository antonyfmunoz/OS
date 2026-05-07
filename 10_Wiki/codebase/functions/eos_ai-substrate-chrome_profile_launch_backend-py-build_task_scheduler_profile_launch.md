---
type: codebase-function
file: eos_ai/substrate/chrome_profile_launch_backend.py
line: 115
generated: 2026-05-07
---

# build_task_scheduler_profile_launch

**File:** [[eos_ai-substrate-chrome_profile_launch_backend-py]] | **Line:** 115
**Signature:** `build_task_scheduler_profile_launch(profile_directory, chrome_path, url, task_name) → dict[str, str]`

Build Task Scheduler commands for profile-specific Chrome launch.

Returns dict with 'create', 'run', and 'delete' commands.
Uses /IT for interactive user session.

## Called By

- [[eos_ai-substrate-chrome_profile_launch_backend-py-build_ssh_cleanup_command]]
- [[eos_ai-substrate-chrome_profile_launch_backend-py-build_ssh_profile_launch_sequence]]
