---
type: codebase-file
path: scripts/substrate_session_orchestration_cli.py
module: scripts.substrate_session_orchestration_cli
lines: 165
size: 5031
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_session_orchestration_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Session Orchestration CLI — operator visibility into session topology.

Usage:
    python3 scripts/substrate_session_orchestration_cli.py status
    python3 scripts/substrate_session_orchestration_cli.py health
...

**Lines:** 165 | **Size:** 5,031 bytes

## Contains

- **fn** [[scripts-substrate_session_orchestration_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_session_orchestration_cli-py-cmd_status]]`(_args) → int`
- **fn** [[scripts-substrate_session_orchestration_cli-py-cmd_health]]`(_args) → int`
- **fn** [[scripts-substrate_session_orchestration_cli-py-cmd_ensure]]`(_args) → int`
- **fn** [[scripts-substrate_session_orchestration_cli-py-cmd_recover]]`(args) → int`
- **fn** [[scripts-substrate_session_orchestration_cli-py-cmd_reconcile]]`(_args) → int`
- **fn** [[scripts-substrate_session_orchestration_cli-py-cmd_expected]]`(_args) → int`
- **fn** [[scripts-substrate_session_orchestration_cli-py-cmd_actual]]`(args) → int`
- **fn** [[scripts-substrate_session_orchestration_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_session_orchestration_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import dataclasses
import json
import sys
```
