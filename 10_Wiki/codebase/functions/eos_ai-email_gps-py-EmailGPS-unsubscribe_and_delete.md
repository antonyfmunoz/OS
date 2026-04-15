---
type: codebase-function
file: eos_ai/email_gps.py
line: 914
generated: 2026-04-12
---

# EmailGPS.unsubscribe_and_delete

**File:** [[eos_ai-email_gps-py]] | **Line:** 914
**Signature:** `unsubscribe_and_delete(email_id, email_preview) → bool`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Unsubscribe then delete. Priority order:
  1. Gmail native API (List-Unsubscribe header — most reliable)
  2. URL extracted from preview → browser agent
  3. Just delete if all fail

## Calls

- [[eos_ai-email_gps-py-EmailGPS-_browser_unsubscribe]]
- [[eos_ai-email_gps-py-EmailGPS-_delete_email]]
- [[eos_ai-email_gps-py-EmailGPS-unsubscribe_via_gmail_api]]
