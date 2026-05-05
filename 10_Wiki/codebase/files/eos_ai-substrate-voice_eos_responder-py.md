---
type: codebase-file
path: eos_ai/substrate/voice_eos_responder.py
module: eos_ai.substrate.voice_eos_responder
lines: 339
size: 12247
generated: 2026-04-12
---

# eos_ai/substrate/voice_eos_responder.py

Voice → EOS responder bridge.

Purpose
-------
This is the first real intelligence adapter for the bounded voice session
...

**Lines:** 339 | **Size:** 12,247 bytes

## Depends On

- [[eos_ai-substrate-voice_session-py]]

## Used By

- [[scripts-substrate_voice_eos_responder_smoke_test-py]]
- [[scripts-substrate_voice_router_responder_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-voice_eos_responder-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-_system_prompt_for]]`(role_slug) → str`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-_build_prompt]]`(session, utterance) → str`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-_record_responder_meta]]`(session) → None`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-_safe_fallback_text]]`(role, reason) → str`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-_route_role]]`(session_role) → str`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-_eos_voice_responder]]`(session, utterance) → str`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-build_eos_voice_responder]]`() → VoiceResponder`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-install_default_eos_voice_responder]]`() → None`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-is_eos_voice_responder_installed]]`() → bool`
- **fn** [[eos_ai-substrate-voice_eos_responder-py-uninstall_eos_voice_responder]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
from typing import Optional
from eos_ai.substrate.voice_session import VoiceResponder
from eos_ai.substrate.voice_session import VoiceSession
from eos_ai.substrate.voice_session import set_voice_responder
```
