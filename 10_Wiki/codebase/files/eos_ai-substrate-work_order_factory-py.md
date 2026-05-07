---
type: codebase-file
path: eos_ai/substrate/work_order_factory.py
module: eos_ai.substrate.work_order_factory
lines: 193
size: 6267
generated: 2026-05-07
---

# eos_ai/substrate/work_order_factory.py

Work order factory for Phase 93R.1.

Additive-only module. Creates pre-configured WorkOrder instances
for known task types. Does not import from or modify any existing
substrate module.

**Lines:** 193 | **Size:** 6,267 bytes

## Depends On

- [[eos_ai-substrate-work_order_contracts-py]]

## Used By

- [[eos_ai-substrate-work_order_dispatch-py]]

## Contains

- **fn** [[eos_ai-substrate-work_order_factory-py-create_google_workspace_discovery_work_order]]`(source_targets, timeout_minutes, assigned_to_node) → WorkOrder`
- **fn** [[eos_ai-substrate-work_order_factory-py-create_google_docs_read_export_work_order]]`(document_titles, folder_path, timeout_minutes, assigned_to_node) → WorkOrder`
- **fn** [[eos_ai-substrate-work_order_factory-py-validate_work_order]]`(wo) → list[str]`
- **fn** [[eos_ai-substrate-work_order_factory-py-work_order_to_bridge_payload]]`(wo) → dict`
- **fn** [[eos_ai-substrate-work_order_factory-py-save_work_order]]`(wo, directory) → Path`
- **fn** [[eos_ai-substrate-work_order_factory-py-load_work_order]]`(path) → WorkOrder`

## Import Statements

```python
from __future__ import annotations
import json
from pathlib import Path
from eos_ai.substrate.work_order_contracts import UNIVERSAL_BLOCKED_ACTIONS
from eos_ai.substrate.work_order_contracts import AuthorityMode
from eos_ai.substrate.work_order_contracts import SensitivityLevel
from eos_ai.substrate.work_order_contracts import WorkOrder
from eos_ai.substrate.work_order_contracts import WorkOrderStatus
from eos_ai.substrate.work_order_contracts import WorkOrderTaskType
from eos_ai.substrate.work_order_contracts import _generate_work_order_id
from eos_ai.substrate.work_order_contracts import _now_iso
```
