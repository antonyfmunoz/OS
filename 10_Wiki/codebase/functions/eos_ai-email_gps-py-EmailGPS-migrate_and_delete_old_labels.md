---
type: codebase-function
file: eos_ai/email_gps.py
line: 1313
generated: 2026-04-12
---

# EmailGPS.migrate_and_delete_old_labels

**File:** [[eos_ai-email_gps-py]] | **Line:** 1313
**Signature:** `migrate_and_delete_old_labels(old_to_new_map) → dict`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Migrate emails from old labels to new GPS labels, then delete old labels.

old_to_new_map: {'1 - To Respond': 'To Respond', ...}
Uses GWSConnector CLI methods — no direct API access needed.

...
