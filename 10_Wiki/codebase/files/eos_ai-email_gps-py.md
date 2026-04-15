---
type: codebase-file
path: eos_ai/email_gps.py
module: eos_ai.email_gps
lines: 1463
size: 56875
generated: 2026-04-12
---

# eos_ai/email_gps.py

EmailGPS — Dan Martell's 7-folder email management system for DEX.

Antony never touches email until DEX has processed it first. Ever.
"I am no longer ever, ever allowed to touch an email that wasn't first
checked by my assistant." — Dan Martell, Buy Back Your Time
...

**Lines:** 1463 | **Size:** 56,875 bytes

## Used By

- [[scripts-inbox_gps_afternoon-py]]
- [[scripts-inbox_zero_init-py]]

## Contains

- **class** [[eos_ai-email_gps-py-EmailFolder]] — 0 methods
- **class** [[eos_ai-email_gps-py-ProcessedEmail]] — 0 methods
- **class** [[eos_ai-email_gps-py-EmailGPS]] — 31 methods

## Import Statements

```python
import asyncio
import re
import subprocess
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Optional
```
