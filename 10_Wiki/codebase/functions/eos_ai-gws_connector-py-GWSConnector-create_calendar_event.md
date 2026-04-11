---
type: codebase-function
file: eos_ai/gws_connector.py
line: 176
generated: 2026-04-11
---

# GWSConnector.create_calendar_event

**File:** [[eos_ai-gws_connector-py]] | **Line:** 176
**Signature:** `create_calendar_event(title, start_iso, duration_minutes, attendee_email, description) → dict | None`

**Class:** [[eos_ai-gws_connector-py-GWSConnector]]

Create a Google Calendar event with a Google Meet link.
start_iso: ISO datetime string (UTC). Defaults to now + 5 minutes.
Returns dict with title, start, meet_link, event_id or None on failure.

## Calls

- [[eos_ai-gws_connector-py-GWSConnector-_run]]

## Called By

- [[eos_ai-gws_connector-py-GWSConnector-block_travel_time]]
