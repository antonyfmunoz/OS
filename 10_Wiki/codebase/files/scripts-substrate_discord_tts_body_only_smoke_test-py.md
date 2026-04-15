---
type: codebase-file
path: scripts/substrate_discord_tts_body_only_smoke_test.py
module: scripts.substrate_discord_tts_body_only_smoke_test
lines: 299
size: 10678
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_discord_tts_body_only_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord TTS Body-Only Split — smoke test.

Proves:
  1. Visible Discord message retains the full reply (footer, skill block,
     provider badge — all preserved).
...

**Lines:** 299 | **Size:** 10,678 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-discord_text_transport-py]]
- [[eos_ai-substrate-tts_sanitize-py]]

## Contains

- **class** [[scripts-substrate_discord_tts_body_only_smoke_test-py-_FakeResponderOK]] — 2 methods
- **fn** [[scripts-substrate_discord_tts_body_only_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_discord_tts_body_only_smoke_test-py-_clear_env]]`() → None`
- **fn** [[scripts-substrate_discord_tts_body_only_smoke_test-py-_enable_and_allow]]`() → None`
- **fn** [[scripts-substrate_discord_tts_body_only_smoke_test-py-_install_fake_responder]]`(reply) → None`
- **fn** [[scripts-substrate_discord_tts_body_only_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from eos_ai.substrate import discord_text_transport as dtt
from eos_ai.substrate.discord_text_transport import build_tts_reply_envelope
from eos_ai.substrate.discord_text_transport import maybe_mirror_discord_text_message
from eos_ai.substrate.discord_text_transport import pseudo_live_status
from eos_ai.substrate.discord_text_transport import reset_backend_state_for_tests
from eos_ai.substrate.discord_text_transport import reset_text_history_for_tests
from eos_ai.substrate.tts_sanitize import sanitize_tts_reply
```
