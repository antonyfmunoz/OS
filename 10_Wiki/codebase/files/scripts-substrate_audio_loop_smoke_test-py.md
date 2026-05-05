---
type: codebase-file
path: scripts/substrate_audio_loop_smoke_test.py
module: scripts.substrate_audio_loop_smoke_test
lines: 293
size: 11744
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_audio_loop_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Audio loop smoke test.

Proves the bounded local audio loop layer end-to-end:

  1. Reset all substrate stores (voice, wake, operator state, audio loop).
...

**Lines:** 293 | **Size:** 11,744 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-operator_state-py]]
- [[eos_ai-substrate-operator_transitions-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-transcript_inject-py]]
- [[eos_ai-substrate-voice_session-py]]
- [[eos_ai-substrate-wake_producer-py]]

## Contains

- **fn** [[scripts-substrate_audio_loop_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_audio_loop_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
import time
from eos_ai.substrate.audio_loop import AudioLoopStatus
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.local_listener import get_trigger_history
from eos_ai.substrate.operator_state import OperatorMode
from eos_ai.substrate.operator_state import get_operator_state_store
from eos_ai.substrate.operator_state import reset_operator_state_store_for_tests
from eos_ai.substrate.operator_transitions import TransitionTrigger
from eos_ai.substrate.operator_transitions import _record_transition
from eos_ai.substrate.operator_transitions import decide_transition
from eos_ai.substrate.result_query import audio_loop_snapshot
from eos_ai.substrate.result_query import recent_audio_loop_transcripts
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.transcript_inject import inject_transcript
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
from eos_ai.substrate.wake_producer import get_wake_producer_history
from eos_ai.substrate.wake_producer import get_wake_producer_runtime
from eos_ai.substrate.wake_producer import reset_wake_producer_runtime_for_tests
```
