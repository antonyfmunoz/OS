---
type: codebase-file
path: eos_ai/substrate/local_control.py
module: eos_ai.substrate.local_control
lines: 946
size: 34195
generated: 2026-05-07
---

# eos_ai/substrate/local_control.py

Local control — safe OS-level action layer for the local machine.

NOT raw shell access. This is structured machine control with mode
enforcement. Every action goes through a permission check before it can
execute, and the current LocalControlMode gates what categories of
...

**Lines:** 946 | **Size:** 34,195 bytes

## Contains

- **class** [[eos_ai-substrate-local_control-py-LocalControlAction]] — 0 methods
- **class** [[eos_ai-substrate-local_control-py-LocalControlMode]] — 0 methods
- **class** [[eos_ai-substrate-local_control-py-RequestStatus]] — 0 methods
- **class** [[eos_ai-substrate-local_control-py-LocalControlRequest]] — 4 methods
- **class** [[eos_ai-substrate-local_control-py-LocalControlStore]] — 14 methods
- **fn** [[eos_ai-substrate-local_control-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-local_control-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-local_control-py-_make_id]]`() → str`
- **fn** [[eos_ai-substrate-local_control-py-is_action_allowed]]`(action, mode) → bool`
- **fn** [[eos_ai-substrate-local_control-py-submit_control_request]]`(action, payload) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-execute_control_request]]`(request_id) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_browser_open_url]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_browser_click]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_browser_type]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_browser_press_keys]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_browser_screenshot]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_subprocess_open_app]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_subprocess_focus_app]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_subprocess_list_windows]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_move_mouse]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-_action_kind_to_control_action]]`(kind_value) → Optional[LocalControlAction]`
- **fn** [[eos_ai-substrate-local_control-py-_dispatch_open_scene]]`(req) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-open_scene]]`(scene_name) → LocalControlRequest`
- **fn** [[eos_ai-substrate-local_control-py-get_local_control_summary]]`() → dict`

## Import Statements

```python
from __future__ import annotations
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from enum import Enum
from typing import Any
from typing import Optional
```
