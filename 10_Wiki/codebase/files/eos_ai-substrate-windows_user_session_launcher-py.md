---
type: codebase-file
path: eos_ai/substrate/windows_user_session_launcher.py
module: eos_ai.substrate.windows_user_session_launcher
lines: 158
size: 5397
generated: 2026-05-07
---

# eos_ai/substrate/windows_user_session_launcher.py

Windows user-session launcher for Phase 94D.8B.

Uses Windows Task Scheduler to execute commands in the interactive
user desktop session. This is the correct way to launch visible GUI
applications from a remote/service context on Windows.
...

**Lines:** 158 | **Size:** 5,397 bytes

## Contains

- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_create_scheduled_task_command]]`(task_name, chrome_path, url) → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_run_scheduled_task_command]]`(task_name) → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_delete_scheduled_task_command]]`(task_name) → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_query_scheduled_task_command]]`(task_name) → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_full_launch_sequence]]`() → list[str]`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_cleanup_command]]`() → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_ssh_create_and_run_command]]`() → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_ssh_cleanup_command]]`() → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-classify_launch_context]]`() → str`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-build_action_attempted_message]]`(exit_code, task_output) → dict[str, Any]`
- **fn** [[eos_ai-substrate-windows_user_session_launcher-py-get_why_task_scheduler]]`() → str`

## Import Statements

```python
from __future__ import annotations
from typing import Any
```
