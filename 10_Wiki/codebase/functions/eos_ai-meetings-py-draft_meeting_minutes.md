---
type: codebase-function
file: eos_ai/meetings.py
line: 655
generated: 2026-04-12
---

# draft_meeting_minutes

**File:** [[eos_ai-meetings-py]] | **Line:** 655
**Signature:** `draft_meeting_minutes(title, person, outcomes, open_loops, duration_minutes, attendee_emails, ctx) → dict`

Draft formal meeting minutes and save to Drive.
Returns dict with 'minutes' (str) and 'drive_file' (dict).

## Called By

- [[eos_ai-meetings-py-update_meeting_outcome]]
