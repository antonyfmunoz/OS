---
type: codebase-file
path: core/adapter_package_manager/adapter_package_readiness.py
module: core.adapter_package_manager.adapter_package_readiness
lines: 127
size: 4155
generated: 2026-05-07
---

# core/adapter_package_manager/adapter_package_readiness.py

Adapter Package Readiness evaluation.

Computes maturity percentages for packages and access paths,
enforces 100% target, and produces honest gap reports.

...

**Lines:** 127 | **Size:** 4,155 bytes

## Contains

- **class** [[core-adapter_package_manager-adapter_package_readiness-py-PackageGapReport]] — 1 methods
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-_evaluate_checks]]`(snap, capability) → list[tuple[str, bool]]`
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-compute_package_maturity_percent]]`(snap, capability) → float`
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-compute_access_path_maturity_percent]]`(path_status) → float`
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-package_targets_100_percent]]`(snap) → bool`
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-access_path_targets_100_percent]]`(path_status) → bool`
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-package_current_state_is_honest]]`(snap, capability) → bool`
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-package_can_be_used_for_capability]]`(snap, capability) → bool`
- **fn** [[core-adapter_package_manager-adapter_package_readiness-py-build_package_gap_report]]`(snap, capability) → PackageGapReport`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from maturity_enforcement import AdapterPackageSnapshot
from maturity_enforcement import _MATURITY_CHECKS
from maturity_enforcement import selected_access_path_is_complete
from maturity_enforcement import known_gaps_affect_capability
```
