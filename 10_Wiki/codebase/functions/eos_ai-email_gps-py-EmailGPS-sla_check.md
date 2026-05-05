---
type: codebase-function
file: eos_ai/email_gps.py
line: 1104
generated: 2026-04-12
---

# EmailGPS.sla_check

**File:** [[eos_ai-email_gps-py]] | **Line:** 1104
**Signature:** `sla_check() → list[dict]`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Check TO_RESPOND emails older than 24h with no draft.
Returns list of SLA breaches sorted by age descending.

## Calls

- [[eos_ai-email_gps-py-EmailGPS-get_emails_to_respond]]
