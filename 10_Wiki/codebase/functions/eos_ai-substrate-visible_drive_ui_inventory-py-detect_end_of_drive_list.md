---
type: codebase-function
file: eos_ai/substrate/visible_drive_ui_inventory.py
line: 156
generated: 2026-05-07
---

# detect_end_of_drive_list

**File:** [[eos_ai-substrate-visible_drive_ui_inventory-py]] | **Line:** 156
**Signature:** `detect_end_of_drive_list(observation_history, min_stable_rounds) → bool`

Detect when we've reached the end of the Drive file list.

Returns True if the last N observations returned the same items,
meaning scrolling is no longer revealing new content.
