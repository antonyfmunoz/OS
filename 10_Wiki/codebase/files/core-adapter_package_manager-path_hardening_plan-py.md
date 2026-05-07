---
type: codebase-file
path: core/adapter_package_manager/path_hardening_plan.py
module: core.adapter_package_manager.path_hardening_plan
lines: 217
size: 7666
generated: 2026-05-07
---

# core/adapter_package_manager/path_hardening_plan.py

Path Hardening Plan for Adapter Packages.

Creates explicit work orders for maturing access paths to 100%.

UMH substrate subsystem. EOS is one platform consumer.

**Lines:** 217 | **Size:** 7,666 bytes

## Contains

- **class** [[core-adapter_package_manager-path_hardening_plan-py-PathHardeningWorkOrder]] — 1 methods
- **fn** [[core-adapter_package_manager-path_hardening_plan-py-create_hardening_work_order]]`(decision) → PathHardeningWorkOrder`
- **fn** [[core-adapter_package_manager-path_hardening_plan-py-create_hardening_plan_for_package]]`(package_id, path_decisions) → list[PathHardeningWorkOrder]`
- **fn** [[core-adapter_package_manager-path_hardening_plan-py-prioritize_hardening_work_orders]]`(work_orders) → list[PathHardeningWorkOrder]`
- **fn** [[core-adapter_package_manager-path_hardening_plan-py-build_path_hardening_plan_report]]`(work_orders) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from full_path_maturity import AdapterPathMaturityDecision
from full_path_maturity import AdapterPathSnapshot
```
