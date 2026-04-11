---
type: codebase-file
path: eos_ai/substrate/meeting_sources.py
module: eos_ai.substrate.meeting_sources
lines: 174
size: 5432
generated: 2026-04-11
---

# eos_ai/substrate/meeting_sources.py

Meeting transcript SOURCE protocol + bounded fakes.

A "meeting source" is a PULL-style producer of utterances captured from a
meeting surface. The MeetingTransport can attach one or more sources and
periodically pump them; each utterance is then routed through the existing
...

**Lines:** 174 | **Size:** 5,432 bytes

## Used By

- [[eos_ai-substrate-google_meet_source-py]]
- [[eos_ai-substrate-meeting_transport-py]]
- [[scripts-substrate_google_meet_smoke_test-py]]
- [[scripts-substrate_meeting_attachment_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-meeting_sources-py-MeetingSourceProtocol]] — 2 methods
- **class** [[eos_ai-substrate-meeting_sources-py-FakeMeetingSource]] — 4 methods
- **class** [[eos_ai-substrate-meeting_sources-py-LiveMeetingSourceStub]] — 3 methods
- **fn** [[eos_ai-substrate-meeting_sources-py-is_meeting_source]]`(obj) → bool`

## Import Statements

```python
from __future__ import annotations
import threading
from collections import deque
from typing import Any
from typing import Callable
from typing import Optional
from typing import Protocol
from typing import runtime_checkable
```
