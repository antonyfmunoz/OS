---
type: codebase-file
path: scripts/substrate_discord_voice_transport_smoke_test.py
module: scripts.substrate_discord_voice_transport_smoke_test
lines: 205
size: 7960
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_discord_voice_transport_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord voice transport smoke test.

Proves the bounded transcript-only Discord transport adapter end-to-end:
  1. DiscordVoiceTransport(...) constructs without any network/client.
  2. Auto-registers a discord_vc_* node so VoiceSessionRuntime accepts it.
...

**Lines:** 205 | **Size:** 7,960 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-discord_voice_transport-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_discord_voice_transport_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.discord_voice_transport import DiscordVoiceTransport
from eos_ai.substrate.discord_voice_transport import get_default_discord_voice_transport
from eos_ai.substrate.discord_voice_transport import get_transport_history
from eos_ai.substrate.discord_voice_transport import maybe_mirror_discord_utterance
from eos_ai.substrate.discord_voice_transport import reset_default_discord_voice_transports_for_tests
from eos_ai.substrate.discord_voice_transport import reset_transport_history_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
