---
type: codebase-file
path: eos_ai/substrate/chrome_accessibility_launch_backend.py
module: eos_ai.substrate.chrome_accessibility_launch_backend
lines: 131
size: 3842
generated: 2026-05-07
---

# eos_ai/substrate/chrome_accessibility_launch_backend.py

Chrome accessibility launch backend for Phase 95.1.

Launches Chrome with --force-renderer-accessibility so that
Windows UI Automation / accessibility tree can read web page content.

...

**Lines:** 131 | **Size:** 3,842 bytes

## Contains

- **fn** [[eos_ai-substrate-chrome_accessibility_launch_backend-py-classify_backend]]`() → str`
- **fn** [[eos_ai-substrate-chrome_accessibility_launch_backend-py-validate_accessibility_flags]]`(flags) → list[str]`
- **fn** [[eos_ai-substrate-chrome_accessibility_launch_backend-py-build_chrome_accessibility_launch_command]]`(chrome_path, profile_directory, url) → str`
- **fn** [[eos_ai-substrate-chrome_accessibility_launch_backend-py-build_task_scheduler_accessibility_launch]]`(profile_directory, chrome_path, url, task_name) → dict[str, str]`
- **fn** [[eos_ai-substrate-chrome_accessibility_launch_backend-py-build_ssh_accessibility_launch_sequence]]`(profile_directory) → list[str]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
```
