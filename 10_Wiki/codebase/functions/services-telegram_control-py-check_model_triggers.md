---
type: codebase-function
file: services/telegram_control.py
line: 2205
generated: 2026-04-12
---

# check_model_triggers

**File:** [[services-telegram_control-py]] | **Line:** 2205
**Signature:** `check_model_triggers(text, prefs) → str | None`

Pure string matching — no AI call.
Returns a response string if a model control trigger matched, else None.

## Called By

- [[services-telegram_control-py-handle_natural_message]]
