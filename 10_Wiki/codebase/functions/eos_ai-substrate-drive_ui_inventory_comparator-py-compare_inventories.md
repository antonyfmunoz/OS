---
type: codebase-function
file: eos_ai/substrate/drive_ui_inventory_comparator.py
line: 34
generated: 2026-05-07
---

# compare_inventories

**File:** [[eos_ai-substrate-drive_ui_inventory_comparator-py]] | **Line:** 34
**Signature:** `compare_inventories(api_inventory, cu_items) → dict[str, Any]`

Compare computer-use inventory against API baseline.

Returns comparison report with:
- matching items
- missing from CU (in API but not CU)
...

## Calls

- [[eos_ai-substrate-drive_ui_inventory_comparator-py-_rate_confidence]]
- [[eos_ai-substrate-drive_ui_inventory_comparator-py-build_api_baseline_names]]
- [[eos_ai-substrate-drive_ui_inventory_comparator-py-build_cu_names]]
