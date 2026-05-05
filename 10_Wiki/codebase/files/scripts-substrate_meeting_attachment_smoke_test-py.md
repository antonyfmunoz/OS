---
type: codebase-file
path: scripts/substrate_meeting_attachment_smoke_test.py
module: scripts.substrate_meeting_attachment_smoke_test
lines: 204
size: 7135
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_meeting_attachment_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Slice A smoke test: real meeting attachment seam.

Proves MeetingTransport.attach_source / pump_attached_sources / detach_source
work end-to-end through the existing bounded inject_transcript seam, without
touching the hot path or creating a parallel agent loop.

**Lines:** 204 | **Size:** 7,135 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-meeting_sources-py]]
- [[eos_ai-substrate-meeting_transport-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_meeting_attachment_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_meeting_attachment_smoke_test-py-_fail]]`(msg) → None`
- **fn** [[scripts-substrate_meeting_attachment_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from dotenv import load_dotenv
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.meeting_sources import FakeMeetingSource
from eos_ai.substrate.meeting_transport import MeetingTransport
from eos_ai.substrate.meeting_transport import reset_default_meeting_transports_for_tests
from eos_ai.substrate.meeting_transport import reset_meeting_transport_history_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
