---
type: codebase-file
path: eos_ai/substrate/tts_sanitize.py
module: eos_ai.substrate.tts_sanitize
lines: 173
size: 6165
generated: 2026-04-11
---

# eos_ai/substrate/tts_sanitize.py

TTS reply sanitization — strip Claude Code / provider footer noise.

Purpose
-------
Claude Code tmux sessions (and legacy provider responses) sometimes append
...

**Lines:** 173 | **Size:** 6,165 bytes

## Used By

- [[scripts-substrate_discord_claude_hardswitch_smoke_test-py]]
- [[scripts-substrate_discord_tts_body_only_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-tts_sanitize-py-_clip]]`(text, max_chars) → str`
- **fn** [[eos_ai-substrate-tts_sanitize-py-sanitize_tts_reply]]`(text) → str`

## Import Statements

```python
from __future__ import annotations
import re
```
