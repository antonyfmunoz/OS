---
type: codebase-file
path: eos_ai/substrate/drive_ui_inventory_comparator.py
module: eos_ai.substrate.drive_ui_inventory_comparator
lines: 155
size: 5123
generated: 2026-05-07
---

# eos_ai/substrate/drive_ui_inventory_comparator.py

Drive UI inventory comparator for Phase 95.0.

Compares a computer-use-derived Drive inventory against the API baseline
to validate the fallback path's accuracy.

...

**Lines:** 155 | **Size:** 5,123 bytes

## Depends On

- [[eos_ai-substrate-local_gui_control_contracts-py]]

## Contains

- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-normalize_name_for_comparison]]`(name) → str`
- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-build_api_baseline_names]]`(api_inventory) → set[str]`
- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-build_cu_names]]`(cu_items) → set[str]`
- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-compare_inventories]]`(api_inventory, cu_items) → dict[str, Any]`
- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-_rate_confidence]]`(score) → str`
- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-find_name_mismatches]]`(api_inventory, cu_items, threshold) → list[dict[str, str]]`
- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-_similarity_ratio]]`(a, b) → float`
- **fn** [[eos_ai-substrate-drive_ui_inventory_comparator-py-build_comparison_report]]`(comparison, mismatches, observation_method) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate.local_gui_control_contracts import GUIInventoryItem
```
