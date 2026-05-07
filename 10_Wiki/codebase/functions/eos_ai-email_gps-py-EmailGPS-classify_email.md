---
type: codebase-function
file: eos_ai/email_gps.py
line: 452
generated: 2026-05-07
---

# EmailGPS.classify_email

**File:** [[eos_ai-email_gps-py]] | **Line:** 452
**Signature:** `classify_email(email) → EmailFolder`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Route email to correct GPS folder.

Two hard rules handle the obvious cases (~40% of inbox):
  1. Financial keyword in subject → RECEIPTS
  2. Unsubscribe in body → NEWSLETTERS
...

## Calls

- [[eos_ai-email_gps-py-EmailGPS-_check_person_recognition]]
- [[eos_ai-email_gps-py-EmailGPS-_classify_by_rules]]
- [[eos_ai-email_gps-py-EmailGPS-_classify_with_ai]]

## Called By

- [[eos_ai-email_gps-py-EmailGPS-process_inbox]]
- [[eos_ai-email_gps-py-EmailGPS-reclassify_folder]]
