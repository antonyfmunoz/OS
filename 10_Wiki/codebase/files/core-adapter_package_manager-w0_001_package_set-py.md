---
type: codebase-file
path: core/adapter_package_manager/w0_001_package_set.py
module: core.adapter_package_manager.w0_001_package_set
lines: 186
size: 5740
generated: 2026-05-07
---

# core/adapter_package_manager/w0_001_package_set.py

W0-001 Adapter Package Set.

Composes Core + Drive API + Docs API + Drive CU + Docs CU into
the W0-001 operational test package set.

...

**Lines:** 186 | **Size:** 5,740 bytes

## Contains

- **class** [[core-adapter_package_manager-w0_001_package_set-py-W0001PackageSetReadiness]] — 1 methods
- **fn** [[core-adapter_package_manager-w0_001_package_set-py-_build_w0_001_members]]`() → list[PackageSetMember]`
- **fn** [[core-adapter_package_manager-w0_001_package_set-py-build_w0_001_adapter_package_set]]`() → PackageSet`
- **fn** [[core-adapter_package_manager-w0_001_package_set-py-evaluate_w0_001_package_set_readiness]]`() → W0001PackageSetReadiness`
- **fn** [[core-adapter_package_manager-w0_001_package_set-py-w0_001_api_slice_is_ready]]`() → bool`
- **fn** [[core-adapter_package_manager-w0_001_package_set-py-w0_001_cu_slice_is_ready]]`() → bool`
- **fn** [[core-adapter_package_manager-w0_001_package_set-py-w0_001_full_triple_test_ready]]`() → bool`
- **fn** [[core-adapter_package_manager-w0_001_package_set-py-build_w0_001_package_set_report]]`() → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from package_set_contracts import PackageSet
from package_set_contracts import PackageSetMember
from package_set_contracts import PackageSetStatus
from package_set_contracts import build_package_set
from package_set_contracts import package_set_all_required_members_mature
from package_set_contracts import package_set_api_ready
from package_set_contracts import package_set_cu_ready
from package_set_contracts import summarize_package_set
```
