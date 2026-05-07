---
type: codebase-file
path: eos_ai/platforms/eos/live_runtime.py
module: eos_ai.platforms.eos.live_runtime
lines: 528
size: 19432
generated: 2026-05-07
---

# eos_ai/platforms/eos/live_runtime.py

EALiveRuntime — Conversational state machine for real-time EA interaction.

Manages the full lifecycle of a live founder conversation:
control-phrase interception, intent routing via EA orchestrator,
immediate execution via execution bridge, and live session binding.
...

**Lines:** 528 | **Size:** 19,432 bytes

## Contains

- **class** [[eos_ai-platforms-eos-live_runtime-py-RuntimeState]] — 0 methods
- **class** [[eos_ai-platforms-eos-live_runtime-py-LiveRuntimeResult]] — 1 methods
- **class** [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime]] — 10 methods
- **fn** [[eos_ai-platforms-eos-live_runtime-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-_utcnow]]`() → str`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-_classify_control_phrase]]`(text) → Optional[str]`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-get_live_runtime]]`() → EALiveRuntime`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-handle_live_user_utterance]]`(text) → LiveRuntimeResult`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-pause_live_runtime]]`() → dict`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-resume_live_runtime]]`() → dict`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-stop_live_runtime]]`() → dict`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-interrupt_live_runtime]]`(new_text) → LiveRuntimeResult`
- **fn** [[eos_ai-platforms-eos-live_runtime-py-format_live_progress_update]]`() → str`

## Import Statements

```python
from __future__ import annotations
import re
import sys
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional
```
