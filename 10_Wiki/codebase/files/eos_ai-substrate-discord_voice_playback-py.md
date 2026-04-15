---
type: codebase-file
path: eos_ai/substrate/discord_voice_playback.py
module: eos_ai.substrate.discord_voice_playback
lines: 651
size: 23243
generated: 2026-04-12
---

# eos_ai/substrate/discord_voice_playback.py

Discord voice playback — bounded TTS adapter on top of the transport.

Purpose
-------
Take a single piece of EOS reply text and play it back into an attached
...

**Lines:** 651 | **Size:** 23,243 bytes

## Used By

- [[scripts-substrate_discord_voice_playback_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-discord_voice_playback-py-PlaybackResult]] — 1 methods
- **class** [[eos_ai-substrate-discord_voice_playback-py-_PlaybackHistory]] — 4 methods
- **class** [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback]] — 10 methods
- **fn** [[eos_ai-substrate-discord_voice_playback-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-discord_voice_playback-py-_utcnow_iso]]`() → str`
- **fn** [[eos_ai-substrate-discord_voice_playback-py-probe_playback_capability]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_voice_playback-py-get_playback_history]]`() → _PlaybackHistory`
- **fn** [[eos_ai-substrate-discord_voice_playback-py-reset_playback_history_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-discord_voice_playback-py-_render_tts_to_wav]]`(text) → Optional[str]`
- **fn** [[eos_ai-substrate-discord_voice_playback-py-playback_env_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-discord_voice_playback-py-normalize_playback_result]]`(raw) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
```
