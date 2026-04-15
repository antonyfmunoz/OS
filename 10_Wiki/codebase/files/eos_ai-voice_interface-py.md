---
type: codebase-file
path: eos_ai/voice_interface.py
module: eos_ai.voice_interface
lines: 801
size: 30429
generated: 2026-04-12
---

# eos_ai/voice_interface.py

VoiceInterface — dedicated voice conversation and meeting intelligence layer.

Wraps MediaProcessor synthesis/transcription into a clean interface for:
  - Full voice conversation turns (transcribe → CognitiveLoop → synthesize)
  - Meeting session capture (accumulate transcript without synthesis)
...

**Lines:** 801 | **Size:** 30,429 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-context-py]]
- [[eos_ai-media_processor-py]]

## Contains

- **class** [[eos_ai-voice_interface-py-VoiceInterface]] — 14 methods

## Import Statements

```python
import os
import re
import time
import uuid
from eos_ai.context import EOSContext
from eos_ai.media_processor import MediaProcessor
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.agent_runtime import TaskType
```
