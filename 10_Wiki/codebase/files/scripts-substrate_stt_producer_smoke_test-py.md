---
type: codebase-file
path: scripts/substrate_stt_producer_smoke_test.py
module: scripts.substrate_stt_producer_smoke_test
lines: 259
size: 9270
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_stt_producer_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

STT producer smoke test.

Proves the bounded local STT/mic capture producer end-to-end:

  1. Reset all substrate stores (voice, wake, operator, audio loop, stt).
...

**Lines:** 259 | **Size:** 9,270 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-operator_state-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-stt_producer-py]]
- [[eos_ai-substrate-voice_session-py]]
- [[eos_ai-substrate-wake_producer-py]]

## Contains

- **fn** [[scripts-substrate_stt_producer_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_stt_producer_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.audio_loop import AudioLoopStatus
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.local_listener import get_trigger_history
from eos_ai.substrate.operator_state import get_operator_state_store
from eos_ai.substrate.operator_state import reset_operator_state_store_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.stt_producer import SttCaptureSource
from eos_ai.substrate.stt_producer import SttCaptureStatus
from eos_ai.substrate.stt_producer import get_local_stt_runtime
from eos_ai.substrate.stt_producer import get_stt_capture_history
from eos_ai.substrate.stt_producer import recent_stt_captures
from eos_ai.substrate.stt_producer import reset_local_stt_runtime_for_tests
from eos_ai.substrate.stt_producer import reset_stt_capture_history_for_tests
from eos_ai.substrate.stt_producer import stt_capture_snapshot
from eos_ai.substrate.stt_producer import stt_runtime_status
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
from eos_ai.substrate.wake_producer import get_wake_producer_history
from eos_ai.substrate.wake_producer import reset_wake_producer_runtime_for_tests
```
