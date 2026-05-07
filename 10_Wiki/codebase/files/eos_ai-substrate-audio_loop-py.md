---
type: codebase-file
path: eos_ai/substrate/audio_loop.py
module: eos_ai.substrate.audio_loop
lines: 613
size: 21831
generated: 2026-05-07
---

# eos_ai/substrate/audio_loop.py

Audio loop — bounded local interaction-window model.

Purpose
-------
Until now the substrate tracked voice sessions (VoiceSession), wake events
...

**Lines:** 613 | **Size:** 21,831 bytes

## Used By

- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_discord_text_tts_smoke_test-py]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py]]
- [[scripts-substrate_google_meet_smoke_test-py]]
- [[scripts-substrate_meeting_attachment_smoke_test-py]]
- [[scripts-substrate_meeting_transport_smoke_test-py]]
- [[scripts-substrate_ptt_binding_smoke_test-py]]
- [[scripts-substrate_stt_producer_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-audio_loop-py-AudioLoopStatus]] — 0 methods
- **class** [[eos_ai-substrate-audio_loop-py-TranscriptEntry]] — 2 methods
- **class** [[eos_ai-substrate-audio_loop-py-AudioLoopState]] — 4 methods
- **class** [[eos_ai-substrate-audio_loop-py-AudioLoopStore]] — 11 methods
- **fn** [[eos_ai-substrate-audio_loop-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-audio_loop-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-audio_loop-py-_parse_iso]]`(ts) → Optional[datetime]`
- **fn** [[eos_ai-substrate-audio_loop-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-substrate-audio_loop-py-get_audio_loop_store]]`() → AudioLoopStore`
- **fn** [[eos_ai-substrate-audio_loop-py-reset_audio_loop_store_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-audio_loop-py-_set_status]]`(state, new_status) → AudioLoopState`
- **fn** [[eos_ai-substrate-audio_loop-py-mark_primed]]`(node_id) → Optional[AudioLoopState]`
- **fn** [[eos_ai-substrate-audio_loop-py-mark_listening]]`(node_id) → Optional[AudioLoopState]`
- **fn** [[eos_ai-substrate-audio_loop-py-mark_responding]]`(node_id) → Optional[AudioLoopState]`
- **fn** [[eos_ai-substrate-audio_loop-py-mark_cooling_down]]`(node_id) → Optional[AudioLoopState]`
- **fn** [[eos_ai-substrate-audio_loop-py-mark_inactive]]`(node_id) → Optional[AudioLoopState]`
- **fn** [[eos_ai-substrate-audio_loop-py-record_transcript]]`(node_id, text) → Optional[TranscriptEntry]`
- **fn** [[eos_ai-substrate-audio_loop-py-should_speak_presence_line]]`(node_id) → bool`
- **fn** [[eos_ai-substrate-audio_loop-py-record_spoken_line]]`(node_id) → Optional[AudioLoopState]`
- **fn** [[eos_ai-substrate-audio_loop-py-snapshot]]`(node_id) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
```
