---
type: codebase-file
path: core/environment_bridge/windows_desktop_adapter_contracts.py
module: core.environment_bridge.windows_desktop_adapter_contracts
lines: 181
size: 6290
generated: 2026-05-07
---

# core/environment_bridge/windows_desktop_adapter_contracts.py

Windows Interactive Desktop Adapter Contracts.

Typed contracts for GUI action requests routed through the Windows
Interactive Desktop Adapter. The adapter runs in the logged-in
Windows user session and has real desktop access — WSL/tmux does not.
...

**Lines:** 181 | **Size:** 6,290 bytes

## Contains

- **class** [[core-environment_bridge-windows_desktop_adapter_contracts-py-WindowsDesktopActionType]] — 0 methods
- **class** [[core-environment_bridge-windows_desktop_adapter_contracts-py-WindowsDesktopAdapterStatus]] — 0 methods
- **class** [[core-environment_bridge-windows_desktop_adapter_contracts-py-WindowsDesktopProofStatus]] — 0 methods
- **class** [[core-environment_bridge-windows_desktop_adapter_contracts-py-WindowsDesktopActionRequest]] — 1 methods
- **class** [[core-environment_bridge-windows_desktop_adapter_contracts-py-WindowsDesktopActionResult]] — 1 methods
- **class** [[core-environment_bridge-windows_desktop_adapter_contracts-py-WindowsDesktopProofArtifact]] — 1 methods
- **class** [[core-environment_bridge-windows_desktop_adapter_contracts-py-WindowsDesktopRelayPaths]] — 2 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any
```
