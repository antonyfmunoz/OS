---
type: codebase-function
file: eos_ai/error_handler.py
line: 186
generated: 2026-04-12
---

# ErrorHandler.handle

**File:** [[eos_ai-error_handler-py]] | **Line:** 186
**Signature:** `handle(error, context, error_type, fallback_fn) → dict`

**Class:** [[eos_ai-error_handler-py-ErrorHandler]]

Main entry point. Returns:
    {resolved: bool, action: str, should_pause: bool}

action: 'fallback' | 'skip' | 'pause' | 'unknown'
should_pause: True signals caller to stop and let Docker restart

## Calls

- [[eos_ai-error_handler-py-ErrorHandler-_log_error]]
- [[eos_ai-error_handler-py-ErrorHandler-_send_alert]]
- [[eos_ai-error_handler-py-ErrorHandler-classify_error]]

## Called By

- [[services-dm_monitor-py-main]]
