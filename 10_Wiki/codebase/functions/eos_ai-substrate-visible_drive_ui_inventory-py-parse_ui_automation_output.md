---
type: codebase-function
file: eos_ai/substrate/visible_drive_ui_inventory.py
line: 240
generated: 2026-05-07
---

# parse_ui_automation_output

**File:** [[eos_ai-substrate-visible_drive_ui_inventory-py]] | **Line:** 240
**Signature:** `parse_ui_automation_output(raw_output) → list[GUIInventoryItem]`

Parse Windows UI Automation output into inventory items.

Expected format from PowerShell UI Automation:
One line per data item, tab-separated or structured.

## Calls

- [[eos_ai-substrate-visible_drive_ui_inventory-py-extract_file_name_from_visible_row]]
- [[eos_ai-substrate-visible_drive_ui_inventory-py-extract_modified_date_from_visible_row]]
- [[eos_ai-substrate-visible_drive_ui_inventory-py-infer_file_type_from_visible_row]]
