---
type: codebase-function
file: eos_ai/email_gps.py
line: 693
generated: 2026-04-11
---

# EmailGPS.process_inbox

**File:** [[eos_ai-email_gps-py]] | **Line:** 693
**Signature:** `process_inbox(limit, process_all, show_progress) → dict`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Fetch emails and route each to a GPS folder.

process_all=True on first run to achieve immediate Inbox Zero
across ALL existing emails (not just unread).

## Calls

- [[eos_ai-email_gps-py-EmailGPS-apply_label_to_email]]
- [[eos_ai-email_gps-py-EmailGPS-capture_email_tasks]]
- [[eos_ai-email_gps-py-EmailGPS-classify_email]]
- [[eos_ai-email_gps-py-EmailGPS-draft_response]]
