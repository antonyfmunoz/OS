---
type: codebase-file
path: scripts/substrate_voice_router_responder_smoke_test.py
module: scripts.substrate_voice_router_responder_smoke_test
lines: 201
size: 6707
generated: 2026-04-12
---

# scripts/substrate_voice_router_responder_smoke_test.py

Voice-session router responder smoke test.

Proves that the live Discord pseudo-live path wires the router-backed
voice responder (eos_ai.substrate.voice_eos_responder._eos_voice_responder)
as the global responder for voice sessions, replacing the substrate's
...

**Lines:** 201 | **Size:** 6,707 bytes

## Depends On

- [[eos_ai-model_router-py]]
- [[eos_ai-substrate-voice_eos_responder-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **class** [[scripts-substrate_voice_router_responder_smoke_test-py-_FakeResult]] — 1 methods
- **fn** [[scripts-substrate_voice_router_responder_smoke_test-py-_section]]`(title) → None`
- **fn** [[scripts-substrate_voice_router_responder_smoke_test-py-_assert]]`(cond, msg) → None`
- **fn** [[scripts-substrate_voice_router_responder_smoke_test-py-_fake_call_with_fallback]]`()`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from eos_ai.substrate.voice_eos_responder import install_default_eos_voice_responder
from eos_ai.substrate.voice_eos_responder import is_eos_voice_responder_installed
from eos_ai.substrate.voice_eos_responder import uninstall_eos_voice_responder
import eos_ai.model_router as _mr
from eos_ai.substrate.voice_session import VoiceSession
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import _default_responder
```
