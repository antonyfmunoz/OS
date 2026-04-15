---
type: codebase-class
file: eos_ai/error_handler.py
line: 130
generated: 2026-04-12
---

# ErrorHandler

**File:** [[eos_ai-error_handler-py]] | **Line:** 130

Classify → log → recover → alert.

One instance per service. Maintains per-error-type alert cooldown
state so repeat alerts are suppressed for ALERT_COOLDOWN seconds.

## Methods

- [[eos_ai-error_handler-py-ErrorHandler-__init__]]`(service_name, ctx)` — 
- [[eos_ai-error_handler-py-ErrorHandler-classify_error]]`(error, context) → str` — Map an exception to a policy key. Rules-based — no LLM call.
- [[eos_ai-error_handler-py-ErrorHandler-handle]]`(error, context, error_type, fallback_fn) → dict` — Main entry point. Returns:
- [[eos_ai-error_handler-py-ErrorHandler-_send_alert]]`(error_type, policy, error, context) → None` — Send a single Telegram alert with 1-hour per-type cooldown.
- [[eos_ai-error_handler-py-ErrorHandler-_log_error]]`(error, error_type, context) → None` — Log error to Neon events table. Silent on all failures.
