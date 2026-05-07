---
type: codebase-function
file: services/handlers/cc_command_handler.py
line: 546
generated: 2026-05-07
---

# try_inline_commands

**File:** [[services-handlers-cc_command_handler-py]] | **Line:** 546
**Signature:** `try_inline_commands(message, text, pending_events) → bool`

Try all inline command handlers.
Returns True if one handled the message.

## Calls

- [[services-handlers-cc_command_handler-py-handle_calendar_write]]
- [[services-handlers-cc_command_handler-py-handle_confirm_event]]
