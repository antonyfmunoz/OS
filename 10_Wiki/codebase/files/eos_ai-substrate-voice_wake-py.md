---
type: codebase-file
path: eos_ai/substrate/voice_wake.py
module: eos_ai.substrate.voice_wake
lines: 381
size: 13212
generated: 2026-05-07
---

# eos_ai/substrate/voice_wake.py

Voice wake — local station input layer for wake word, clap trigger, and
voice/TTS mode state.

Purpose
-------
...

**Lines:** 381 | **Size:** 13,212 bytes

## Contains

- **class** [[eos_ai-substrate-voice_wake-py-WakeTrigger]] — 0 methods
- **class** [[eos_ai-substrate-voice_wake-py-StationMode]] — 0 methods
- **class** [[eos_ai-substrate-voice_wake-py-VoiceWakeState]] — 3 methods
- **class** [[eos_ai-substrate-voice_wake-py-VoiceWakeStore]] — 7 methods
- **class** [[eos_ai-substrate-voice_wake-py-WakeWordAdapter]] — 1 methods
- **class** [[eos_ai-substrate-voice_wake-py-ClapAdapter]] — 1 methods
- **fn** [[eos_ai-substrate-voice_wake-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-voice_wake-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-voice_wake-py-enable_wake]]`() → VoiceWakeState`
- **fn** [[eos_ai-substrate-voice_wake-py-disable_wake]]`() → VoiceWakeState`
- **fn** [[eos_ai-substrate-voice_wake-py-enable_clap]]`() → VoiceWakeState`
- **fn** [[eos_ai-substrate-voice_wake-py-disable_clap]]`() → VoiceWakeState`
- **fn** [[eos_ai-substrate-voice_wake-py-enable_tts]]`() → VoiceWakeState`
- **fn** [[eos_ai-substrate-voice_wake-py-disable_tts]]`() → VoiceWakeState`
- **fn** [[eos_ai-substrate-voice_wake-py-register_trigger]]`(trigger) → VoiceWakeState`
- **fn** [[eos_ai-substrate-voice_wake-py-get_voice_wake_summary]]`() → dict`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional
```
