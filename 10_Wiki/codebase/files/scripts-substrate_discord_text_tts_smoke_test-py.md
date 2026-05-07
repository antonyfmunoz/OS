---
type: codebase-file
path: scripts/substrate_discord_text_tts_smoke_test.py
module: scripts.substrate_discord_text_tts_smoke_test
lines: 276
size: 10194
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_discord_text_tts_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord Pseudo-Live Voice Loop v1 — smoke test.

Proves the bounded Discord text-channel ingress + TTS reply envelope
end-to-end WITHOUT requiring a live Discord client.

...

**Lines:** 276 | **Size:** 10,194 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-discord_text_transport-py]]
- [[eos_ai-substrate-discord_voice_transport-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_discord_text_tts_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_discord_text_tts_smoke_test-py-_clear_env]]`() → None`
- **fn** [[scripts-substrate_discord_text_tts_smoke_test-py-_bootstrap_shared_node]]`() → str`
- **fn** [[scripts-substrate_discord_text_tts_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.discord_text_transport import build_tts_reply_envelope
from eos_ai.substrate.discord_text_transport import ingest_text_message
from eos_ai.substrate.discord_text_transport import get_text_history
from eos_ai.substrate.discord_text_transport import maybe_mirror_discord_text_message
from eos_ai.substrate.discord_text_transport import pseudo_live_status
from eos_ai.substrate.discord_text_transport import reset_text_history_for_tests
from eos_ai.substrate.discord_text_transport import truncate_reply
from eos_ai.substrate.discord_voice_transport import get_default_discord_voice_transport
from eos_ai.substrate.discord_voice_transport import reset_default_discord_voice_transports_for_tests
from eos_ai.substrate.discord_voice_transport import reset_transport_history_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
