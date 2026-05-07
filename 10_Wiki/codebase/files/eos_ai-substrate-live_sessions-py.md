---
type: codebase-file
path: eos_ai/substrate/live_sessions.py
module: eos_ai.substrate.live_sessions
lines: 635
size: 24278
generated: 2026-05-07
---

# eos_ai/substrate/live_sessions.py

Live sessions — real-time continuous interaction layer for the substrate.

Purpose
-------
This module supports real-time continuous sessions with one or more agent
...

**Lines:** 635 | **Size:** 24,278 bytes

## Contains

- **class** [[eos_ai-substrate-live_sessions-py-LiveSessionState]] — 0 methods
- **class** [[eos_ai-substrate-live_sessions-py-LiveSessionType]] — 0 methods
- **class** [[eos_ai-substrate-live_sessions-py-LiveSession]] — 4 methods
- **class** [[eos_ai-substrate-live_sessions-py-LiveSessionStore]] — 12 methods
- **fn** [[eos_ai-substrate-live_sessions-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-live_sessions-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-live_sessions-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-live_sessions-py-_get_current_day_session_id]]`() → Optional[str]`
- **fn** [[eos_ai-substrate-live_sessions-py-_get_and_validate]]`(live_session_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-create_live_session]]`(title, session_type) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-start_live_session]]`(live_session_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-pause_live_session]]`(live_session_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-resume_live_session]]`(live_session_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-end_live_session]]`(live_session_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-fail_live_session]]`(live_session_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-attach_task_to_live_session]]`(live_session_id, task_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-attach_pipeline_to_live_session]]`(live_session_id, pipeline_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-detach_task_from_live_session]]`(live_session_id, task_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-detach_pipeline_from_live_session]]`(live_session_id, pipeline_id) → LiveSession`
- **fn** [[eos_ai-substrate-live_sessions-py-get_live_session_summary]]`() → dict`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import Optional
```
