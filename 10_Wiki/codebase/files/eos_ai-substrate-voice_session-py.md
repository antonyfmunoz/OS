---
type: codebase-file
path: eos_ai/substrate/voice_session.py
module: eos_ai.substrate.voice_session
lines: 790
size: 29559
generated: 2026-04-12
---

# eos_ai/substrate/voice_session.py

Voice session — bounded live voice-presence layer for the substrate.

Purpose
-------
This module is the first VOICE PRESENCE MVP on top of the existing
...

**Lines:** 790 | **Size:** 29,559 bytes

## Depends On

- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-roles-py]]
- [[eos_ai-substrate-station_helpers-py]]

## Used By

- [[eos_ai-substrate-transcript_inject-py]]
- [[eos_ai-substrate-voice_eos_responder-py]]
- [[eos_ai-substrate-wake_producer-py]]
- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_discord_text_tts_smoke_test-py]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py]]
- [[scripts-substrate_google_meet_smoke_test-py]]
- [[scripts-substrate_meeting_attachment_smoke_test-py]]
- [[scripts-substrate_meeting_transport_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_ptt_binding_smoke_test-py]]
- [[scripts-substrate_stt_producer_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py]]
- [[scripts-substrate_voice_router_responder_smoke_test-py]]
- [[scripts-substrate_voice_session_cli-py]]
- [[scripts-substrate_voice_session_smoke_test-py]]
- [[scripts-substrate_wake_producer_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-voice_session-py-VoiceSessionStatus]] — 1 methods
- **class** [[eos_ai-substrate-voice_session-py-VoiceTurnSource]] — 0 methods
- **class** [[eos_ai-substrate-voice_session-py-VoiceTurn]] — 2 methods
- **class** [[eos_ai-substrate-voice_session-py-VoiceSession]] — 6 methods
- **class** [[eos_ai-substrate-voice_session-py-VoiceSessionStore]] — 13 methods
- **class** [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime]] — 6 methods
- **fn** [[eos_ai-substrate-voice_session-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-voice_session-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-voice_session-py-_new_id]]`(prefix) → str`
- **fn** [[eos_ai-substrate-voice_session-py-get_voice_session_store]]`() → VoiceSessionStore`
- **fn** [[eos_ai-substrate-voice_session-py-reset_voice_session_store_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-voice_session-py-_default_responder]]`(session, utterance) → str`
- **fn** [[eos_ai-substrate-voice_session-py-set_voice_responder]]`(responder) → None`
- **fn** [[eos_ai-substrate-voice_session-py-_apply_operator_state]]`(session, lifecycle) → None`
- **fn** [[eos_ai-substrate-voice_session-py-_call_responder]]`(session, utterance) → str`
- **fn** [[eos_ai-substrate-voice_session-py-voice_session_report]]`(node_id, limit) → dict`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Callable
from typing import Optional
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.roles import AgentRole
from eos_ai.substrate.roles import RoleRegistry
from eos_ai.substrate.station_helpers import propose_speak_text
```
