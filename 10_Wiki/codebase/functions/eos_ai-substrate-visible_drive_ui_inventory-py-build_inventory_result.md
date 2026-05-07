---
type: codebase-function
file: eos_ai/substrate/visible_drive_ui_inventory.py
line: 209
generated: 2026-05-07
---

# build_inventory_result

**File:** [[eos_ai-substrate-visible_drive_ui_inventory-py]] | **Line:** 209
**Signature:** `build_inventory_result(items, observation_method, scroll_count, end_of_list_reached) → dict[str, Any]`

Build the final inventory result from observed items.

## Calls

- [[eos_ai-substrate-local_gui_control_contracts-py-GUIAction-to_dict]]
- [[eos_ai-substrate-local_gui_control_contracts-py-GUIInventoryItem-to_dict]]
- [[eos_ai-substrate-local_gui_control_contracts-py-GUIObservationPolicy-to_dict]]
- [[eos_ai-substrate-local_gui_control_contracts-py-GUIObservationResult-to_dict]]
- [[eos_ai-substrate-visible_drive_ui_inventory-py-dedupe_inventory_items]]

## Called By

- [[eos_ai-substrate-visible_drive_ui_inventory-py-build_complete_cu_inventory]]
