---
type: codebase-function
file: eos_ai/substrate/visible_drive_ui_inventory.py
line: 90
generated: 2026-05-07
---

# extract_file_name_from_visible_row

**File:** [[eos_ai-substrate-visible_drive_ui_inventory-py]] | **Line:** 90
**Signature:** `extract_file_name_from_visible_row(row_text) → str`

Extract the file name from a visible Drive list row.

Drive list view typically shows: [icon] Name [owner] [date] [size]
The name is usually the first substantial text element.
Splits on original separators (tabs, double spaces) before normalizing.

## Calls

- [[eos_ai-substrate-visible_drive_ui_inventory-py-normalize_visible_drive_row]]

## Called By

- [[eos_ai-substrate-visible_drive_ui_inventory-py-parse_ui_automation_output]]
