---
type: codebase-file
path: scripts/substrate_wake_producer_cli.py
module: scripts.substrate_wake_producer_cli
lines: 110
size: 3048
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_wake_producer_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Wake producer CLI — simulate wake-word / clap events and view history.

Bounded. No audio frameworks. No freeform commands. Mirrors the
substrate_voice_session_cli.py idiom. Never raises — errors are printed
as JSON with an "error" key.

**Lines:** 110 | **Size:** 3,048 bytes

## Depends On

- [[eos_ai-substrate-wake_producer-py]]

## Contains

- **fn** [[scripts-substrate_wake_producer_cli-py-_emit]]`(obj) → None`
- **fn** [[scripts-substrate_wake_producer_cli-py-cmd_simulate_wake_word]]`(args) → int`
- **fn** [[scripts-substrate_wake_producer_cli-py-cmd_simulate_clap]]`(args) → int`
- **fn** [[scripts-substrate_wake_producer_cli-py-cmd_report]]`(args) → int`
- **fn** [[scripts-substrate_wake_producer_cli-py-cmd_status]]`(_args) → int`
- **fn** [[scripts-substrate_wake_producer_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_wake_producer_cli-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate.wake_producer import get_wake_producer_runtime
```
