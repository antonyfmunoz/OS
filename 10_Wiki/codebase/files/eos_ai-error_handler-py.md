---
type: codebase-file
path: eos_ai/error_handler.py
module: eos_ai.error_handler
lines: 347
size: 13129
generated: 2026-05-07
---

# eos_ai/error_handler.py

ErrorHandler — self-healing error handling with Telegram alerting.

Principle:
  1. Errors attempt auto-recovery first (retry/fallback)
  2. If recovery fails: log to Neon, send ONE Telegram alert, signal pause
...

**Lines:** 347 | **Size:** 13,129 bytes

## Contains

- **class** [[eos_ai-error_handler-py-ErrorSeverity]] — 0 methods
- **class** [[eos_ai-error_handler-py-RecoveryStrategy]] — 0 methods
- **class** [[eos_ai-error_handler-py-ErrorHandler]] — 5 methods
- **fn** [[eos_ai-error_handler-py-with_retry]]`(max_retries, delay, error_types, service)`

## Import Statements

```python
import functools
import os
import time
import traceback
from datetime import datetime
from datetime import timezone
from enum import Enum
```
