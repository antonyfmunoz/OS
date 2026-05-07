---
type: codebase-file
path: eos_ai/event_manager.py
module: eos_ai.event_manager
lines: 267
size: 8367
generated: 2026-05-07
---

# eos_ai/event_manager.py

Event Manager — coordinates conferences, offsites, client dinners,
team events, and speaking engagements. Distinct from calendar events —
these are multi-day or multi-stakeholder events requiring logistics.

**Lines:** 267 | **Size:** 8,367 bytes

## Contains

- **fn** [[eos_ai-event_manager-py-create_event]]`(name, event_type, date, location, attendees, budget, notes, ctx) → dict`
- **fn** [[eos_ai-event_manager-py-get_events]]`(upcoming_only, ctx) → list`
- **fn** [[eos_ai-event_manager-py-log_speaking_engagement]]`(event_name, organizer, organizer_email, date, topic, format, status, ctx) → bool`
- **fn** [[eos_ai-event_manager-py-draft_talking_points]]`(topic, audience, duration_minutes, format, ctx) → str`
- **fn** [[eos_ai-event_manager-py-log_pr_media_inquiry]]`(outlet, contact_name, contact_email, topic, deadline, inquiry_type, ctx) → bool`

## Import Statements

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv
```
