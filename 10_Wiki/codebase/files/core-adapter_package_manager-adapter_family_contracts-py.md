---
type: codebase-file
path: core/adapter_package_manager/adapter_family_contracts.py
module: core.adapter_package_manager.adapter_family_contracts
lines: 154
size: 5054
generated: 2026-05-07
---

# core/adapter_package_manager/adapter_family_contracts.py

Adapter Family Contracts.

Defines the Adapter Family, Service Adapter Package, and related
taxonomy for suite-level ecosystems like Google Workspace.

...

**Lines:** 154 | **Size:** 5,054 bytes

## Contains

- **class** [[core-adapter_package_manager-adapter_family_contracts-py-AdapterFamilyStatus]] — 0 methods
- **class** [[core-adapter_package_manager-adapter_family_contracts-py-ServicePackageStatus]] — 0 methods
- **class** [[core-adapter_package_manager-adapter_family_contracts-py-ServiceAdapterPackageRef]] — 1 methods
- **class** [[core-adapter_package_manager-adapter_family_contracts-py-AdapterFamily]] — 1 methods
- **fn** [[core-adapter_package_manager-adapter_family_contracts-py-build_adapter_family]]`(family_id, family_name, core_package_id, service_packages, future_service_candidates, shared_auth_models, shared_governance, shared_tool_mastery, status) → AdapterFamily`
- **fn** [[core-adapter_package_manager-adapter_family_contracts-py-adapter_family_is_monolithic]]`(family) → bool`
- **fn** [[core-adapter_package_manager-adapter_family_contracts-py-service_blocks_current_test]]`(service_ref) → bool`
- **fn** [[core-adapter_package_manager-adapter_family_contracts-py-family_can_be_fully_mature]]`(family) → bool`
- **fn** [[core-adapter_package_manager-adapter_family_contracts-py-list_declared_services]]`(family) → list[ServiceAdapterPackageRef]`
- **fn** [[core-adapter_package_manager-adapter_family_contracts-py-list_future_candidate_services]]`(family) → list[ServiceAdapterPackageRef]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
