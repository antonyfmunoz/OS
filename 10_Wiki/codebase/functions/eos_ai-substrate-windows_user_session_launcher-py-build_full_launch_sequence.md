---
type: codebase-function
file: eos_ai/substrate/windows_user_session_launcher.py
line: 68
generated: 2026-05-07
---

# build_full_launch_sequence

**File:** [[eos_ai-substrate-windows_user_session_launcher-py]] | **Line:** 68
**Signature:** `build_full_launch_sequence() → list[str]`

Build the complete sequence of commands for Chrome launch via Task Scheduler.

Returns list of commands to execute in order via SSH.

## Calls

- [[eos_ai-substrate-windows_user_session_launcher-py-build_create_scheduled_task_command]]
- [[eos_ai-substrate-windows_user_session_launcher-py-build_run_scheduled_task_command]]
