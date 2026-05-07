---
type: codebase-file
path: eos_ai/substrate/event_spine.py
module: eos_ai.substrate.event_spine
lines: 207
size: 7392
generated: 2026-05-07
---

# eos_ai/substrate/event_spine.py

Event Spine — unified structured event model for EOS substrate.

Every significant action in the substrate layer emits an Event through
this model.  Events carry a ``correlation_id`` that threads an entire
workflow (Discord prompt → pipeline → steps → relay → delivery) into
...

**Lines:** 207 | **Size:** 7,392 bytes

## Contains

- **class** [[eos_ai-substrate-event_spine-py-EventType]] — 0 methods
- **class** [[eos_ai-substrate-event_spine-py-EventStatus]] — 0 methods
- **class** [[eos_ai-substrate-event_spine-py-Event]] — 3 methods
- **fn** [[eos_ai-substrate-event_spine-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-event_spine-py-_new_event_id]]`() → str`
- **fn** [[eos_ai-substrate-event_spine-py-_content_hash]]`(text) → str`
- **fn** [[eos_ai-substrate-event_spine-py-create_event]]`(event_type) → Event`

## Import Statements

```python
from __future__ import annotations
import hashlib
import time
import uuid
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Optional
```
