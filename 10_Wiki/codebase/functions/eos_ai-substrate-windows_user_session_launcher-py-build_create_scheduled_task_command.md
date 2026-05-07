---
type: codebase-function
file: eos_ai/substrate/windows_user_session_launcher.py
line: 34
generated: 2026-05-07
---

# build_create_scheduled_task_command

**File:** [[eos_ai-substrate-windows_user_session_launcher-py]] | **Line:** 34
**Signature:** `build_create_scheduled_task_command(task_name, chrome_path, url) → str`

Build the schtasks command to create an interactive user-session task.

/IT = run only when user is logged on interactively
/RL HIGHEST = run with highest available privileges
/SC ONCE /ST 00:00 = one-time trigger (we'll run it manually)
...

## Called By

- [[eos_ai-substrate-windows_user_session_launcher-py-build_full_launch_sequence]]
- [[eos_ai-substrate-windows_user_session_launcher-py-build_ssh_create_and_run_command]]
