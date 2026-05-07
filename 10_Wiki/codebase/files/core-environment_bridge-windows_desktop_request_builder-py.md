---
type: codebase-file
path: core/environment_bridge/windows_desktop_request_builder.py
module: core.environment_bridge.windows_desktop_request_builder
lines: 82
size: 2724
generated: 2026-05-07
---

# core/environment_bridge/windows_desktop_request_builder.py

Windows Interactive Desktop Request Builder.

Builds typed JSON requests for the Windows Interactive Desktop Adapter
relay. Requests are validated before being emitted.

...

**Lines:** 82 | **Size:** 2,724 bytes

## Contains

- **fn** [[core-environment_bridge-windows_desktop_request_builder-py-build_w0_chrome_open_request]]`(work_order_id, trace_id, url) → WindowsDesktopActionRequest`
- **fn** [[core-environment_bridge-windows_desktop_request_builder-py-build_ping_request]]`(trace_id) → WindowsDesktopActionRequest`
- **fn** [[core-environment_bridge-windows_desktop_request_builder-py-request_to_json]]`(request) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from windows_desktop_adapter_contracts import BLOCKED_LAUNCH_METHODS
from windows_desktop_adapter_contracts import WindowsDesktopActionRequest
from windows_desktop_adapter_contracts import WindowsDesktopActionType
```
