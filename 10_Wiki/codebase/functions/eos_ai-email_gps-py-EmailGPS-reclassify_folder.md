---
type: codebase-function
file: eos_ai/email_gps.py
line: 1216
generated: 2026-04-12
---

# EmailGPS.reclassify_folder

**File:** [[eos_ai-email_gps-py]] | **Line:** 1216
**Signature:** `reclassify_folder(source_folder, limit) → dict`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Pull emails from a folder, re-run classification, move if misclassified.
Use this to fix the To Respond folder after rule updates.

Returns: {moved: N, stayed: N, errors: N}

## Calls

- [[eos_ai-email_gps-py-EmailGPS-apply_label_to_email]]
- [[eos_ai-email_gps-py-EmailGPS-classify_email]]
