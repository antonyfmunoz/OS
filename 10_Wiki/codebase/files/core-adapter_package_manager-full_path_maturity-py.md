---
type: codebase-file
path: core/adapter_package_manager/full_path_maturity.py
module: core.adapter_package_manager.full_path_maturity
lines: 284
size: 11159
generated: 2026-05-07
---

# core/adapter_package_manager/full_path_maturity.py

Full-Path Adapter Package Maturity Contract.

For a full Adapter Package maturity test, every declared access path
must reach 100%. A package with API COMPLETE + CU PARTIAL is not
fully mature if both are declared package paths.
...

**Lines:** 284 | **Size:** 11,159 bytes

## Contains

- **class** [[core-adapter_package_manager-full_path_maturity-py-PathDeclarationStatus]] — 0 methods
- **class** [[core-adapter_package_manager-full_path_maturity-py-FullPathMaturityStatus]] — 0 methods
- **class** [[core-adapter_package_manager-full_path_maturity-py-AdapterPathSnapshot]] — 0 methods
- **class** [[core-adapter_package_manager-full_path_maturity-py-AdapterPathMaturityDecision]] — 1 methods
- **class** [[core-adapter_package_manager-full_path_maturity-py-FullAdapterPackageMaturityDecision]] — 1 methods
- **fn** [[core-adapter_package_manager-full_path_maturity-py-_compute_path_maturity]]`(snap) → tuple[float, list[str]]`
- **fn** [[core-adapter_package_manager-full_path_maturity-py-evaluate_path_maturity]]`(snap, package_id) → AdapterPathMaturityDecision`
- **fn** [[core-adapter_package_manager-full_path_maturity-py-path_counts_toward_package_maturity]]`(decision) → bool`
- **fn** [[core-adapter_package_manager-full_path_maturity-py-path_blocks_full_package_maturity]]`(decision) → bool`
- **fn** [[core-adapter_package_manager-full_path_maturity-py-reject_fake_complete_path]]`(snap) → bool`
- **fn** [[core-adapter_package_manager-full_path_maturity-py-evaluate_full_adapter_package_maturity]]`(package_id, paths) → FullAdapterPackageMaturityDecision`
- **fn** [[core-adapter_package_manager-full_path_maturity-py-build_full_path_maturity_report]]`(decision) → str`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
