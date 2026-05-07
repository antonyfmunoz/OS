---
type: codebase-function
file: eos_ai/error_handler.py
line: 315
generated: 2026-05-07
---

# with_retry

**File:** [[eos_ai-error_handler-py]] | **Line:** 315
**Signature:** `with_retry(max_retries, delay, error_types, service)`

Decorator: retry a function up to max_retries times on error_types.

Usage:
    @with_retry(max_retries=3, delay=10, service='dm_monitor')
    def fetch_inbox():
...
