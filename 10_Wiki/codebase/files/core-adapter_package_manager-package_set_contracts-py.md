---
type: codebase-file
path: core/adapter_package_manager/package_set_contracts.py
module: core.adapter_package_manager.package_set_contracts
lines: 186
size: 6523
generated: 2026-05-07
---

# core/adapter_package_manager/package_set_contracts.py

Package Set Contracts.

A Package Set is a composed operational bundle used for a specific
test or workflow. It selects packages from an Adapter Family and
evaluates readiness for the specific test scope.
...

**Lines:** 186 | **Size:** 6,523 bytes

## Contains

- **class** [[core-adapter_package_manager-package_set_contracts-py-PackageSetStatus]] — 0 methods
- **class** [[core-adapter_package_manager-package_set_contracts-py-PackageSetMember]] — 1 methods
- **class** [[core-adapter_package_manager-package_set_contracts-py-PackageSet]] — 1 methods
- **fn** [[core-adapter_package_manager-package_set_contracts-py-build_package_set]]`(package_set_id, package_set_name, family_id, included_packages, excluded_future_candidates, declared_capabilities) → PackageSet`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-_compute_status]]`(ps) → PackageSetStatus`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-_compute_maturity_summary]]`(ps) → dict[str, Any]`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-_compute_blockers]]`(ps) → list[str]`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-package_set_all_required_members_mature]]`(package_set) → bool`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-package_set_api_ready]]`(package_set) → bool`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-package_set_cu_ready]]`(package_set) → bool`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-package_set_blocks_memory_review]]`(package_set) → bool`
- **fn** [[core-adapter_package_manager-package_set_contracts-py-summarize_package_set]]`(package_set) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
