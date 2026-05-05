---
type: codebase-file
path: scripts/substrate_discord_voice_transport_cli.py
module: scripts.substrate_discord_voice_transport_cli
lines: 238
size: 7160
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_discord_voice_transport_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord voice transport CLI — bounded operator interface to the
Discord voice transport adapter.

Subcommands:
  status      Show transport status_report() for a (guild, channel) pair.
...

**Lines:** 238 | **Size:** 7,160 bytes

## Contains

- **class** [[scripts-substrate_discord_voice_transport_cli-py-_FakeVoiceClient]] — 3 methods
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-_transport]]`(args)`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_status]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_start]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_inject]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_end]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_report]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_attach_fake]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_detach]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_play]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-cmd_playback_status]]`(args) → int`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-_common_target]]`(p) → None`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_discord_voice_transport_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
```
