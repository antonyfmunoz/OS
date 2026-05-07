---
type: codebase-file
path: eos_ai/platforms/eos/streaming_bridge.py
module: eos_ai.platforms.eos.streaming_bridge
lines: 422
size: 14585
generated: 2026-05-07
---

# eos_ai/platforms/eos/streaming_bridge.py

StreamingBridge — real-time execution narration for the immersive runtime.

Bridges execution events into human-consumable feedback: TTS speech,
Discord messages, and live session attachment.  Every action in the system
can emit a streaming event and the bridge routes it to all active outputs.
...

**Lines:** 422 | **Size:** 14,585 bytes

## Contains

- **class** [[eos_ai-platforms-eos-streaming_bridge-py-StreamEventType]] — 0 methods
- **class** [[eos_ai-platforms-eos-streaming_bridge-py-StreamEvent]] — 1 methods
- **class** [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine]] — 6 methods
- **class** [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge]] — 15 methods
- **fn** [[eos_ai-platforms-eos-streaming_bridge-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-streaming_bridge-py-_utcnow]]`() → str`
- **fn** [[eos_ai-platforms-eos-streaming_bridge-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-platforms-eos-streaming_bridge-py-get_streaming_bridge]]`() → StreamingBridge`
- **fn** [[eos_ai-platforms-eos-streaming_bridge-py-stream_event]]`(event_type, message) → StreamEvent`
- **fn** [[eos_ai-platforms-eos-streaming_bridge-py-cancel_speech]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Callable
from typing import Optional
```
