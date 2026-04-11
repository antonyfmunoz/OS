---
type: codebase-file
path: services/handlers/cc_command_handler.py
module: services.handlers.cc_command_handler
lines: 564
size: 20710
generated: 2026-04-11
---

# services/handlers/cc_command_handler.py

Inline command handlers for Discord on_message.
Extracted from discord_bot.py — handles !followup, !travel,
!nomeetings, !confirm_event, !meetingroi, !competitive,
!documents, !audit, !stakeholders, !add_stakeholder,
and calendar write detection.
...

**Lines:** 564 | **Size:** 20,710 bytes

## Contains

- **fn** [[services-handlers-cc_command_handler-py-handle_followup]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_travel]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_nomeetings]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_confirm_event]]`(message, text, pending_events) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_meetingroi]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_competitive]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_documents]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_audit]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_stakeholders]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_add_stakeholder]]`(message, text) → bool`
- **fn** [[services-handlers-cc_command_handler-py-handle_calendar_write]]`(message, text, pending_events) → bool`
- **fn** [[services-handlers-cc_command_handler-py-try_inline_commands]]`(message, text, pending_events) → bool`

## Import Statements

```python
import json
import os
import sys
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
```
