---
type: codebase-file
path: eos_ai/meetings.py
module: eos_ai.meetings
lines: 854
size: 30615
generated: 2026-04-12
---

# eos_ai/meetings.py

Meetings — central module for all meeting lifecycle management.
Neon + Notion + Discord all three on every action.

**Lines:** 854 | **Size:** 30,615 bytes

## Contains

- **fn** [[eos_ai-meetings-py-create_meeting_record]]`(title, person, email, company, date_iso, meeting_type, venture, source, meet_link, calendly_event_id, ctx) → dict`
- **fn** [[eos_ai-meetings-py-update_meeting_outcome]]`(calendly_event_id, notion_id, status, outcomes, open_loops, ctx) → bool`
- **fn** [[eos_ai-meetings-py-update_meeting_prep_notes]]`(notion_id, prep_notes) → bool`
- **fn** [[eos_ai-meetings-py-find_notion_meeting_by_person]]`(person) → str | None`
- **fn** [[eos_ai-meetings-py-get_open_loop_meetings]]`(days_back, ctx) → list[dict]`
- **fn** [[eos_ai-meetings-py-queue_follow_up_tasks]]`(person, open_loops, venture, ctx) → bool`
- **fn** [[eos_ai-meetings-py-build_prep_brief]]`(person, company, meeting_type, venture, email, ctx) → str`
- **fn** [[eos_ai-meetings-py-draft_meeting_agenda]]`(title, person, email, meeting_type, venture, duration_minutes, ctx) → str`
- **fn** [[eos_ai-meetings-py-draft_meeting_minutes]]`(title, person, outcomes, open_loops, duration_minutes, attendee_emails, ctx) → dict`
- **fn** [[eos_ai-meetings-py-calculate_meeting_roi]]`(venture, days, ctx) → dict`

## Import Statements

```python
import os
import json
import logging
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo
```
