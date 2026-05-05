---
type: codebase-file
path: scripts/substrate_ptt_binding_cli.py
module: scripts.substrate_ptt_binding_cli
lines: 121
size: 3794
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_ptt_binding_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Workstation push-to-talk binding CLI.

Subcommands:
  readiness   Show stt_workstation_readiness() (exit 0 if real_ready).
  devices     List enumerable input audio devices.
...

**Lines:** 121 | **Size:** 3,794 bytes

## Contains

- **fn** [[scripts-substrate_ptt_binding_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_ptt_binding_cli-py-cmd_readiness]]`(args) → int`
- **fn** [[scripts-substrate_ptt_binding_cli-py-cmd_devices]]`(args) → int`
- **fn** [[scripts-substrate_ptt_binding_cli-py-cmd_validate]]`(args) → int`
- **fn** [[scripts-substrate_ptt_binding_cli-py-cmd_report]]`(args) → int`
- **fn** [[scripts-substrate_ptt_binding_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_ptt_binding_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
```
