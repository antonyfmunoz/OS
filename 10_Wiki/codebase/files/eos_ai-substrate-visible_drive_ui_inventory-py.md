---
type: codebase-file
path: eos_ai/substrate/visible_drive_ui_inventory.py
module: eos_ai.substrate.visible_drive_ui_inventory
lines: 423
size: 13626
generated: 2026-05-07
---

# eos_ai/substrate/visible_drive_ui_inventory.py

Visible Drive UI inventory for Phase 95.0.

Extracts file/folder metadata from the visible Google Drive UI
using only computer-use methods (observation, mouse, keyboard, scroll).

...

**Lines:** 423 | **Size:** 13,626 bytes

## Depends On

- [[eos_ai-substrate-local_gui_control_contracts-py]]

## Contains

- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-validate_inventory_scope]]`(scope) → list[str]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-normalize_visible_drive_row]]`(text) → str`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-extract_file_name_from_visible_row]]`(row_text) → str`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-extract_modified_date_from_visible_row]]`(row_text) → str`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-infer_file_type_from_visible_row]]`(row_text) → str`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-dedupe_inventory_items]]`(items) → list[GUIInventoryItem]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-detect_end_of_drive_list]]`(observation_history, min_stable_rounds) → bool`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-build_scroll_plan]]`(max_scrolls, scroll_delay_ms, observe_after_scroll) → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-build_inventory_result]]`(items, observation_method, scroll_count, end_of_list_reached) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-parse_ui_automation_output]]`(raw_output) → list[GUIInventoryItem]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-capture_visible_drive_rows_from_accessibility_tree]]`(raw_tree_text) → list[dict[str, str]]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-extract_drive_item_from_row]]`(row) → GUIInventoryItem`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-detect_new_items]]`(previous_items, current_items) → list[GUIInventoryItem]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-should_continue_scrolling]]`(history, max_scrolls, no_new_item_limit) → bool`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-build_scroll_action]]`(direction, amount) → dict[str, str]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-build_complete_cu_inventory]]`(items, method, scroll_count, baseline_count) → dict[str, Any]`
- **fn** [[eos_ai-substrate-visible_drive_ui_inventory-py-mark_inventory_incomplete]]`(current_count, baseline_count, reason) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import re
from typing import Any
from eos_ai.substrate.local_gui_control_contracts import GUIInventoryItem
from eos_ai.substrate.local_gui_control_contracts import GUIObservationMethod
from eos_ai.substrate.local_gui_control_contracts import GUIObservationResult
```
