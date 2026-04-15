---
type: codebase-file
path: eos_ai/substrate/discord_voice_transport.py
module: eos_ai.substrate.discord_voice_transport
lines: 805
size: 30582
generated: 2026-04-12
---

# eos_ai/substrate/discord_voice_transport.py

Discord voice transport — bounded adapter onto the existing voice substrate.

Purpose
-------
This module is the FIRST Discord voice transport adapter. It exists so that
...

**Lines:** 805 | **Size:** 30,582 bytes

## Used By

- [[scripts-substrate_discord_text_tts_smoke_test-py]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-discord_voice_transport-py-DiscordTransportEvent]] — 1 methods
- **class** [[eos_ai-substrate-discord_voice_transport-py-_TransportHistory]] — 4 methods
- **class** [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport]] — 13 methods
- **fn** [[eos_ai-substrate-discord_voice_transport-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-_utcnow_iso]]`() → str`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-_probe_discord_capability]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-get_transport_history]]`() → _TransportHistory`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-reset_transport_history_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-_build_node_id]]`(guild_id, channel_id) → str`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-get_default_discord_voice_transport]]`() → DiscordVoiceTransport`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-reset_default_discord_voice_transports_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-_env_hook_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-_playback_env_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-maybe_attach_discord_voice_client]]`(voice_client) → Optional[dict[str, Any]]`
- **fn** [[eos_ai-substrate-discord_voice_transport-py-maybe_mirror_discord_utterance]]`(text) → Optional[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
import os
import sys
import threading
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
```
