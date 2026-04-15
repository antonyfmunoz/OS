---
type: codebase-file
path: eos_ai/substrate/google_meet_source.py
module: eos_ai.substrate.google_meet_source
lines: 355
size: 12755
generated: 2026-04-12
---

# eos_ai/substrate/google_meet_source.py

Google Meet transcript SOURCE adapter.

First REAL provider adapter on top of the bounded MeetingSourceProtocol /
MeetingTransport seam. Transcript-only. Pull-based. Never raises.

...

**Lines:** 355 | **Size:** 12,755 bytes

## Depends On

- [[eos_ai-substrate-meeting_sources-py]]

## Used By

- [[scripts-substrate_google_meet_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-google_meet_source-py-GoogleMeetSource]] — 11 methods
- **fn** [[eos_ai-substrate-google_meet_source-py-_truthy_env]]`(name) → bool`
- **fn** [[eos_ai-substrate-google_meet_source-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-google_meet_source-py-parse_meet_url]]`(url_or_code) → Optional[str]`
- **fn** [[eos_ai-substrate-google_meet_source-py-is_google_meet_source]]`(obj) → bool`

## Import Statements

```python
from __future__ import annotations
import os
import re
import threading
from collections import deque
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable
from typing import Optional
from eos_ai.substrate.meeting_sources import is_meeting_source
```
