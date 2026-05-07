---
type: codebase-function
file: eos_ai/substrate/windows_user_session_launcher.py
line: 84
generated: 2026-05-07
---

# build_ssh_create_and_run_command

**File:** [[eos_ai-substrate-windows_user_session_launcher-py]] | **Line:** 84
**Signature:** `build_ssh_create_and_run_command() → str`

Build the full SSH command that creates and runs the scheduled task.

This is the single command the VPS sends to the local PC.
Creates the task, then immediately runs it.

## Calls

- [[eos_ai-substrate-windows_user_session_launcher-py-build_create_scheduled_task_command]]
- [[eos_ai-substrate-windows_user_session_launcher-py-build_run_scheduled_task_command]]
