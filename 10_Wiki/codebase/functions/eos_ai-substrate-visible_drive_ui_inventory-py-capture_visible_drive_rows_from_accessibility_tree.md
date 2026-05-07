---
type: codebase-function
file: eos_ai/substrate/visible_drive_ui_inventory.py
line: 278
generated: 2026-05-07
---

# capture_visible_drive_rows_from_accessibility_tree

**File:** [[eos_ai-substrate-visible_drive_ui_inventory-py]] | **Line:** 278
**Signature:** `capture_visible_drive_rows_from_accessibility_tree(raw_tree_text) → list[dict[str, str]]`

Parse raw accessibility tree output into structured rows.

Expected input format (from PowerShell UIAutomation DataItem names):
FILE: FileName FileType Modified DateStr me More actions (Alt+A)
