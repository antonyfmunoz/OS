---
type: codebase-file
path: core/adapter_package_manager/adapter_path_inventory.py
module: core.adapter_package_manager.adapter_path_inventory
lines: 305
size: 11938
generated: 2026-05-07
---

# core/adapter_package_manager/adapter_path_inventory.py

Adapter Path Inventory for W0-001 and Google Workspace.

Inventories all access paths for a tool/platform package with their
declaration status, maturity percent, gaps, and blockers.

...

**Lines:** 305 | **Size:** 11,938 bytes

## Contains

- **class** [[core-adapter_package_manager-adapter_path_inventory-py-AdapterPathInventoryItem]] — 1 methods
- **fn** [[core-adapter_package_manager-adapter_path_inventory-py-_gws_path]]`(path_id, path_name, path_type, declaration, capability, auth, status, mastery, maturity_pct, gaps, blockers) → AdapterPathInventoryItem`
- **fn** [[core-adapter_package_manager-adapter_path_inventory-py-inventory_google_workspace_paths]]`() → list[AdapterPathInventoryItem]`
- **fn** [[core-adapter_package_manager-adapter_path_inventory-py-inventory_claude_code_paths]]`() → list[AdapterPathInventoryItem]`
- **fn** [[core-adapter_package_manager-adapter_path_inventory-py-inventory_w0_001_operational_tools]]`() → list[AdapterPathInventoryItem]`
- **fn** [[core-adapter_package_manager-adapter_path_inventory-py-classify_declared_vs_candidate_paths]]`(items) → tuple[list[AdapterPathInventoryItem], list[AdapterPathInventoryItem]]`
- **fn** [[core-adapter_package_manager-adapter_path_inventory-py-build_adapter_path_inventory_report]]`(items) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from full_path_maturity import PathDeclarationStatus
```
