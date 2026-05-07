---
type: codebase-file
path: eos_ai/substrate/transcript_inject.py
module: eos_ai.substrate.transcript_inject
lines: 205
size: 7285
generated: 2026-05-07
---

# eos_ai/substrate/transcript_inject.py

Transcript injection — the bounded entry point for text-shaped input
into an active (or resumable) voice session.

Purpose
-------
...

**Lines:** 205 | **Size:** 7,285 bytes

## Depends On

- [[eos_ai-substrate-voice_session-py]]

## Used By

- [[scripts-substrate_audio_loop_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-transcript_inject-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-transcript_inject-py-_resolve_active_session_id]]`(node_id) → Optional[str]`
- **fn** [[eos_ai-substrate-transcript_inject-py-inject_transcript]]`(node_id, text) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import sys
from typing import Any
from typing import Optional
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
```
