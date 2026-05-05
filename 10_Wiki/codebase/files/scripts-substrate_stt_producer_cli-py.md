---
type: codebase-file
path: scripts/substrate_stt_producer_cli.py
module: scripts.substrate_stt_producer_cli
lines: 191
size: 6170
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_stt_producer_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

STT producer CLI — bounded operator interface to the local STT capture layer.

Subcommands:
  report              Show stt_runtime_status + capture snapshot + recent.
  capture             Perform one bounded capture on a node.
...

**Lines:** 191 | **Size:** 6,170 bytes

## Contains

- **fn** [[scripts-substrate_stt_producer_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_stt_producer_cli-py-cmd_report]]`(args) → int`
- **fn** [[scripts-substrate_stt_producer_cli-py-cmd_readiness]]`(args) → int`
- **fn** [[scripts-substrate_stt_producer_cli-py-cmd_devices]]`(args) → int`
- **fn** [[scripts-substrate_stt_producer_cli-py-cmd_capture]]`(args) → int`
- **fn** [[scripts-substrate_stt_producer_cli-py-cmd_inject]]`(args) → int`
- **fn** [[scripts-substrate_stt_producer_cli-py-cmd_recent]]`(args) → int`
- **fn** [[scripts-substrate_stt_producer_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_stt_producer_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
```
