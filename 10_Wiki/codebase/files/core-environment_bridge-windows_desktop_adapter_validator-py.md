---
type: codebase-file
path: core/environment_bridge/windows_desktop_adapter_validator.py
module: core.environment_bridge.windows_desktop_adapter_validator
lines: 162
size: 5457
generated: 2026-05-07
---

# core/environment_bridge/windows_desktop_adapter_validator.py

Windows Interactive Desktop Adapter Validator.

Validates action requests before they are written to the relay inbox.
Rejects requests with wrong environment, wrong execution surface role,
disallowed launch methods, missing proof contracts, or missing trace_id.
...

**Lines:** 162 | **Size:** 5,457 bytes

## Contains

- **class** [[core-environment_bridge-windows_desktop_adapter_validator-py-AdapterValidationResult]] — 1 methods
- **fn** [[core-environment_bridge-windows_desktop_adapter_validator-py-validate_desktop_action_request]]`(request) → AdapterValidationResult`
- **fn** [[core-environment_bridge-windows_desktop_adapter_validator-py-validate_desktop_action_request_dict]]`(request_dict) → AdapterValidationResult`
- **fn** [[core-environment_bridge-windows_desktop_adapter_validator-py-_validate_open_url_request]]`(request, result) → None`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from windows_desktop_adapter_contracts import BLOCKED_LAUNCH_METHODS
from windows_desktop_adapter_contracts import WindowsDesktopActionRequest
from windows_desktop_adapter_contracts import WindowsDesktopActionType
```
