---
type: codebase-file
path: eos_ai/substrate/chrome_profile_launch_backend.py
module: eos_ai.substrate.chrome_profile_launch_backend
lines: 202
size: 6002
generated: 2026-05-07
---

# eos_ai/substrate/chrome_profile_launch_backend.py

Chrome profile launch backend for Phase 94D.9.

Launches Google Drive in a specific Chrome profile using the
--profile-directory flag. Uses the proven Task Scheduler /IT path
for visible desktop execution.
...

**Lines:** 202 | **Size:** 6,002 bytes

## Contains

- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-classify_backend]]`() → str`
- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-validate_profile_directory]]`(profile_directory) → list[str]`
- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-validate_drive_url]]`(url) → list[str]`
- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-build_chrome_profile_drive_launch_command]]`(chrome_path, profile_directory, url) → str`
- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-build_task_scheduler_profile_launch]]`(profile_directory, chrome_path, url, task_name) → dict[str, str]`
- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-build_ssh_profile_launch_sequence]]`(profile_directory) → list[str]`
- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-build_ssh_cleanup_command]]`() → str`
- **fn** [[eos_ai-substrate-chrome_profile_launch_backend-py-build_action_attempted_message]]`(profile_directory, exit_code) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
```
