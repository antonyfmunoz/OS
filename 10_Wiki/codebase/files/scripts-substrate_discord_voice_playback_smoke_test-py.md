---
type: codebase-file
path: scripts/substrate_discord_voice_playback_smoke_test.py
module: scripts.substrate_discord_voice_playback_smoke_test
lines: 290
size: 10489
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_discord_voice_playback_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord voice playback smoke test.

Proves the bounded VoiceClient attachment + playback path on top of the
existing Discord voice transport adapter, end-to-end, WITHOUT touching a
real Discord connection.
...

**Lines:** 290 | **Size:** 10,489 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-discord_voice_playback-py]]
- [[eos_ai-substrate-discord_voice_transport-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **class** [[scripts-substrate_discord_voice_playback_smoke_test-py-FakeVoiceClient]] — 3 methods
- **fn** [[scripts-substrate_discord_voice_playback_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_discord_voice_playback_smoke_test-py-_fresh_transport]]`() → DiscordVoiceTransport`
- **fn** [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.discord_voice_playback import DiscordVoicePlayback
from eos_ai.substrate.discord_voice_playback import get_playback_history
from eos_ai.substrate.discord_voice_playback import playback_env_enabled
from eos_ai.substrate.discord_voice_playback import probe_playback_capability
from eos_ai.substrate.discord_voice_playback import reset_playback_history_for_tests
from eos_ai.substrate.discord_voice_transport import DiscordVoiceTransport
from eos_ai.substrate.discord_voice_transport import get_transport_history
from eos_ai.substrate.discord_voice_transport import maybe_attach_discord_voice_client
from eos_ai.substrate.discord_voice_transport import reset_default_discord_voice_transports_for_tests
from eos_ai.substrate.discord_voice_transport import reset_transport_history_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
