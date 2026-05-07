---
type: codebase-file
path: eos_ai/substrate/os_controller.py
module: eos_ai.substrate.os_controller
lines: 713
size: 27232
generated: 2026-05-07
---

# eos_ai/substrate/os_controller.py

OS controller — deep system control surface beyond browser automation.

Extends local_control.py with richer OS-level actions: coordinate-based
mouse control, keyboard automation, file operations, window management,
and optional OCR screen reading.
...

**Lines:** 713 | **Size:** 27,232 bytes

## Contains

- **class** [[eos_ai-substrate-os_controller-py-OSAction]] — 0 methods
- **class** [[eos_ai-substrate-os_controller-py-OSActionResult]] — 1 methods
- **class** [[eos_ai-substrate-os_controller-py-OSController]] — 18 methods
- **fn** [[eos_ai-substrate-os_controller-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-os_controller-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-os_controller-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-substrate-os_controller-py-_has_pyautogui]]`() → bool`
- **fn** [[eos_ai-substrate-os_controller-py-_has_xdotool]]`() → bool`
- **fn** [[eos_ai-substrate-os_controller-py-_has_wmctrl]]`() → bool`
- **fn** [[eos_ai-substrate-os_controller-py-get_os_controller]]`() → OSController`
- **fn** [[eos_ai-substrate-os_controller-py-execute_os_action]]`(action, payload) → OSActionResult`

## Import Statements

```python
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
```
