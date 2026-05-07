---
type: codebase-file
path: core/adapter_package_manager/google_drive_api_package.py
module: core.adapter_package_manager.google_drive_api_package
lines: 116
size: 3737
generated: 2026-05-07
---

# core/adapter_package_manager/google_drive_api_package.py

Google Drive API Adapter Package (W-GDRIVE-API-001).

Drive inventory and metadata extraction for W0-001.
Derived from W-GWS-API-001 where applicable.

...

**Lines:** 116 | **Size:** 3,737 bytes

## Contains

- **class** [[core-adapter_package_manager-google_drive_api_package-py-GoogleDriveApiPackage]] — 1 methods
- **fn** [[core-adapter_package_manager-google_drive_api_package-py-build_google_drive_api_package]]`() → GoogleDriveApiPackage`
- **fn** [[core-adapter_package_manager-google_drive_api_package-py-drive_api_supports_inventory]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_drive_api_package-py-drive_api_supports_metadata]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_drive_api_package-py-drive_api_is_read_only]]`(pkg) → bool`
- **fn** [[core-adapter_package_manager-google_drive_api_package-py-drive_api_inherits_from_legacy]]`(pkg) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
