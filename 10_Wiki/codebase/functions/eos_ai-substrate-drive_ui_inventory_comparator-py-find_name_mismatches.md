---
type: codebase-function
file: eos_ai/substrate/drive_ui_inventory_comparator.py
line: 91
generated: 2026-05-07
---

# find_name_mismatches

**File:** [[eos_ai-substrate-drive_ui_inventory_comparator-py]] | **Line:** 91
**Signature:** `find_name_mismatches(api_inventory, cu_items, threshold) → list[dict[str, str]]`

Find potential name mismatches (similar but not exact).

Uses simple character overlap ratio for fuzzy matching.

## Calls

- [[eos_ai-substrate-drive_ui_inventory_comparator-py-_similarity_ratio]]
- [[eos_ai-substrate-drive_ui_inventory_comparator-py-normalize_name_for_comparison]]
