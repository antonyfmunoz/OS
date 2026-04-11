---
type: codebase-file
path: eos_ai/voice_engine.py
module: eos_ai.voice_engine
lines: 631
size: 25146
generated: 2026-04-11
---

# eos_ai/voice_engine.py

VoiceEngine — intelligent voice layer for Discord.

Handles:
  - Speech-to-text  : faster-whisper (fast, built-in VAD) → OpenAI Whisper fallback
  - Speech detection: Silero VAD (neural) → webrtcvad fallback
...

**Lines:** 631 | **Size:** 25,146 bytes

## Used By

- [[services-discord_bot-py]]

## Contains

- **class** [[eos_ai-voice_engine-py-SpeechClassification]] — 0 methods
- **class** [[eos_ai-voice_engine-py-IntelligentVoiceProcessor]] — 11 methods
- **class** [[eos_ai-voice_engine-py-VADProcessor]] — 4 methods
- **class** [[eos_ai-voice_engine-py-VoiceEngine]] — 10 methods

## Import Statements

```python
import os
import subprocess
import tempfile
import wave
from collections import deque
from datetime import datetime
from pathlib import Path
```
