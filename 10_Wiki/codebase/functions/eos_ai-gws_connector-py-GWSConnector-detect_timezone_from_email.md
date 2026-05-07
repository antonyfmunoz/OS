---
type: codebase-function
file: eos_ai/gws_connector.py
line: 401
generated: 2026-05-07
---

# GWSConnector.detect_timezone_from_email

**File:** [[eos_ai-gws_connector-py]] | **Line:** 401
**Signature:** `detect_timezone_from_email(email) → str`

**Class:** [[eos_ai-gws_connector-py-GWSConnector]]

Detect likely timezone from email domain.
Returns timezone string e.g. 'America/New_York'.
Falls back to 'America/Los_Angeles' (Antony's TZ).

## Called By

- [[eos_ai-gws_connector-py-GWSConnector-format_time_for_attendee]]
