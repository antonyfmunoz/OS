---
type: codebase-file
path: eos_ai/substrate/visible_browser_launch_backend.py
module: eos_ai.substrate.visible_browser_launch_backend
lines: 277
size: 9592
generated: 2026-05-07
---

# eos_ai/substrate/visible_browser_launch_backend.py

Visible browser launch backend for Phase 94D.7R.

Opens a visible URL in Google Chrome on the local machine.
This is NOT Playwright. This does NOT scrape, control DOM, or read content.
It only launches a URL visibly in Chrome.
...

**Lines:** 277 | **Size:** 9,592 bytes

## Contains

- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-classify_backend]]`() → str`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-find_chrome_candidates]]`() → list[str]`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-build_chrome_detection_command]]`() → str`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-build_open_url_in_chrome_command]]`(url) → str`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-validate_url_allowed]]`(url, allowed_domains) → list[str]`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-build_open_url_command]]`(url) → list[list[str]]`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-_is_wsl]]`() → bool`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-build_drive_open_action]]`(target_account) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-build_backend_missing_message]]`(reason) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-execute_chrome_launch]]`(url) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-execute_browser_launch]]`(url) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_browser_launch_backend-py-parse_launch_result]]`(result) → str`

## Import Statements

```python
from __future__ import annotations
import os
import subprocess
from typing import Any
```
