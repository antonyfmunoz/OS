---
type: codebase-file
path: scripts/substrate_voice_session_cli.py
module: scripts.substrate_voice_session_cli
lines: 149
size: 4745
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_voice_session_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Bounded operator CLI for the voice session substrate.

Subcommands:
  start   --node NODE --role ROLE          Start a new voice session.
  say     --session SID --text TEXT        Submit an utterance to a session.
...

**Lines:** 149 | **Size:** 4,745 bytes

## Depends On

- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_voice_session_cli-py-_maybe_install_eos_responder]]`() → None`
- **fn** [[scripts-substrate_voice_session_cli-py-_print_session]]`(session) → int`
- **fn** [[scripts-substrate_voice_session_cli-py-cmd_start]]`(args) → int`
- **fn** [[scripts-substrate_voice_session_cli-py-cmd_say]]`(args) → int`
- **fn** [[scripts-substrate_voice_session_cli-py-cmd_switch]]`(args) → int`
- **fn** [[scripts-substrate_voice_session_cli-py-cmd_end]]`(args) → int`
- **fn** [[scripts-substrate_voice_session_cli-py-cmd_report]]`(args) → int`
- **fn** [[scripts-substrate_voice_session_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_voice_session_cli-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import voice_session_report
```
