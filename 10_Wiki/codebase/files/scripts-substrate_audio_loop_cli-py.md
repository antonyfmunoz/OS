---
type: codebase-file
path: scripts/substrate_audio_loop_cli.py
module: scripts.substrate_audio_loop_cli
lines: 136
size: 4184
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_audio_loop_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Bounded operator CLI for the local audio loop.

Subcommands:
  report                             Snapshot the audio loop across all nodes.
  report-node --node NODE            Snapshot one node + its transcript ring.
...

**Lines:** 136 | **Size:** 4,184 bytes

## Contains

- **fn** [[scripts-substrate_audio_loop_cli-py-_dumps]]`(obj) → str`
- **fn** [[scripts-substrate_audio_loop_cli-py-cmd_report]]`(args) → int`
- **fn** [[scripts-substrate_audio_loop_cli-py-cmd_report_node]]`(args) → int`
- **fn** [[scripts-substrate_audio_loop_cli-py-cmd_inject_transcript]]`(args) → int`
- **fn** [[scripts-substrate_audio_loop_cli-py-cmd_prime]]`(args) → int`
- **fn** [[scripts-substrate_audio_loop_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_audio_loop_cli-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
```
