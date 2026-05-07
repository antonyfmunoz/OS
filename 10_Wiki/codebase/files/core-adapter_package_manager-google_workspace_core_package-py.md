---
type: codebase-file
path: core/adapter_package_manager/google_workspace_core_package.py
module: core.adapter_package_manager.google_workspace_core_package
lines: 128
size: 4285
generated: 2026-05-07
---

# core/adapter_package_manager/google_workspace_core_package.py

Google Workspace Core Foundation Package (W-GWS-CORE-001).

Shared foundation for all Google Workspace service adapter packages.
Contains auth/session model, governance defaults, no-secret policy,
rate limit doctrine, and workspace-level Tool Mastery requirements.
...

**Lines:** 128 | **Size:** 4,285 bytes

## Contains

- **class** [[core-adapter_package_manager-google_workspace_core_package-py-GoogleWorkspaceCorePackage]] — 1 methods
- **fn** [[core-adapter_package_manager-google_workspace_core_package-py-build_google_workspace_core_package]]`() → GoogleWorkspaceCorePackage`
- **fn** [[core-adapter_package_manager-google_workspace_core_package-py-core_has_shared_auth]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_core_package-py-core_has_no_secret_policy]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_core_package-py-core_has_shared_governance]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_core_package-py-core_does_not_imply_gmail]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_workspace_core_package-py-core_does_not_imply_sheets]]`(pkg) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
