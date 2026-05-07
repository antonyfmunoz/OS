---
type: codebase-function
file: eos_ai/email_gps.py
line: 1146
generated: 2026-05-07
---

# EmailGPS.apply_label_to_email

**File:** [[eos_ai-email_gps-py]] | **Line:** 1146
**Signature:** `apply_label_to_email(email_id, folder, method) → bool`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Apply Gmail label to actually move email in the real inbox.
Creates the label if it doesn't exist, then removes INBOX label.
Logs an email_classified event to Neon for the nightly reviewer.

## Calls

- [[eos_ai-email_gps-py-EmailGPS-_log_classification_event]]

## Called By

- [[eos_ai-email_gps-py-EmailGPS-process_inbox]]
- [[eos_ai-email_gps-py-EmailGPS-reclassify_folder]]
