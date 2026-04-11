---
type: codebase-file
path: scripts/substrate_discord_claude_hardswitch_smoke_test.py
module: scripts.substrate_discord_claude_hardswitch_smoke_test
lines: 213
size: 7353
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_discord_claude_hardswitch_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord Claude Primary Backend + TTS Sanitization — smoke test.

Replaces the former "hard-switch" test. The Discord-only bypass has been
removed: Discord text messages now flow through the shared broader router
(eos_ai.model_router.call_with_fallback), where Claude CLI tmux is
...

**Lines:** 213 | **Size:** 7,353 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-discord_text_transport-py]]
- [[eos_ai-substrate-tts_sanitize-py]]

## Contains

- **class** [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-_FakeIngestOK]] — 1 methods
- **fn** [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-_clear_env]]`() → None`
- **fn** [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-_enable_and_allow]]`() → None`
- **fn** [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-main]]`() → int`

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
