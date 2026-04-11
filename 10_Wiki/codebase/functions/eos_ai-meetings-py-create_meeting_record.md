---
type: codebase-function
file: eos_ai/meetings.py
line: 16
generated: 2026-04-11
---

# create_meeting_record

**File:** [[eos_ai-meetings-py]] | **Line:** 16
**Signature:** `create_meeting_record(title, person, email, company, date_iso, meeting_type, venture, source, meet_link, calendly_event_id, ctx) → dict`

Create a meeting record in Neon + Notion simultaneously.
Returns dict with neon_id, notion_id, success.
