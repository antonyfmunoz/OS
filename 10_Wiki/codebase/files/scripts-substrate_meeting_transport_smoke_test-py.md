---
type: codebase-file
path: scripts/substrate_meeting_transport_smoke_test.py
module: scripts.substrate_meeting_transport_smoke_test
lines: 283
size: 11345
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_meeting_transport_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Meeting voice transport smoke test.

Proves the bounded transcript-only meeting transport adapter end-to-end:
  1. MeetingTransport(...) constructs without any browser/client/network.
  2. Auto-registers a meeting_<platform>_<id> node so VoiceSessionRuntime
...

**Lines:** 283 | **Size:** 11,345 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-meeting_transport-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-transport_report-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **class** [[scripts-substrate_meeting_transport_smoke_test-py-_FakeSink]] — 2 methods
- **fn** [[scripts-substrate_meeting_transport_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_meeting_transport_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.meeting_transport import MeetingTransport
from eos_ai.substrate.meeting_transport import get_default_meeting_transport
from eos_ai.substrate.meeting_transport import get_meeting_transport_history
from eos_ai.substrate.meeting_transport import maybe_mirror_meeting_utterance
from eos_ai.substrate.meeting_transport import reset_default_meeting_transports_for_tests
from eos_ai.substrate.meeting_transport import reset_meeting_transport_history_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.transport_report import unified_transport_report
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
