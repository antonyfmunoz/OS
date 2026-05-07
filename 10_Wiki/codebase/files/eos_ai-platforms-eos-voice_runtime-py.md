---
type: codebase-file
path: eos_ai/platforms/eos/voice_runtime.py
module: eos_ai.platforms.eos.voice_runtime
lines: 632
size: 21896
generated: 2026-05-07
---

# eos_ai/platforms/eos/voice_runtime.py

VoiceRuntime — continuous conversational voice loop for the immersive runtime.

Manages the full cycle: mic capture → STT → live_runtime → streaming_bridge → TTS.
Supports always-on listening, wake word activation, push-to-talk, silence
detection, and mid-speech interruption.
...

**Lines:** 632 | **Size:** 21,896 bytes

## Contains

- **class** [[eos_ai-platforms-eos-voice_runtime-py-WakeMode]] — 0 methods
- **class** [[eos_ai-platforms-eos-voice_runtime-py-VoiceLoopState]] — 0 methods
- **class** [[eos_ai-platforms-eos-voice_runtime-py-STTProvider]] — 0 methods
- **class** [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntimeState]] — 1 methods
- **class** [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime]] — 16 methods
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-_utcnow]]`() → str`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-_capture_audio_chunk]]`(duration_s, sample_rate) → Optional[bytes]`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-_detect_silence]]`(audio_bytes, threshold) → bool`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-_detect_wake_word]]`(audio_bytes, wake_phrase) → bool`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-_transcribe_audio]]`(audio_bytes, provider, sample_rate) → Optional[str]`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-get_voice_runtime]]`() → VoiceRuntime`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-start_voice_runtime]]`() → VoiceRuntime`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-stop_voice_runtime]]`() → None`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-get_voice_runtime_state]]`() → dict`
- **fn** [[eos_ai-platforms-eos-voice_runtime-py-interrupt_voice_runtime]]`(new_text) → None`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Callable
from typing import Optional
```
