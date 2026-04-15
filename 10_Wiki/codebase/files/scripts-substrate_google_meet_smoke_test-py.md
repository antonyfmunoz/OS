---
type: codebase-file
path: scripts/substrate_google_meet_smoke_test.py
module: scripts.substrate_google_meet_smoke_test
lines: 284
size: 10003
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_google_meet_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Google Meet source adapter smoke test.

Proves the GoogleMeetSource adapter:
  - parses meet URLs / codes
  - reports honest mode (transcript_only / attached_degraded / attached_live)
...

**Lines:** 284 | **Size:** 10,003 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-google_meet_source-py]]
- [[eos_ai-substrate-meeting_sources-py]]
- [[eos_ai-substrate-meeting_transport-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_google_meet_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_google_meet_smoke_test-py-_fail]]`(msg) → None`
- **fn** [[scripts-substrate_google_meet_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from dotenv import load_dotenv
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.google_meet_source import LIVE_ENV_VAR
from eos_ai.substrate.google_meet_source import PROVIDER
from eos_ai.substrate.google_meet_source import GoogleMeetSource
from eos_ai.substrate.google_meet_source import is_google_meet_source
from eos_ai.substrate.google_meet_source import parse_meet_url
from eos_ai.substrate.meeting_sources import is_meeting_source
from eos_ai.substrate.meeting_transport import MeetingTransport
from eos_ai.substrate.meeting_transport import reset_default_meeting_transports_for_tests
from eos_ai.substrate.meeting_transport import reset_meeting_transport_history_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
