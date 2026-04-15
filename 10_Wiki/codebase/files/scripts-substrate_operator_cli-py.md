---
type: codebase-file
path: scripts/substrate_operator_cli.py
module: scripts.substrate_operator_cli
lines: 229
size: 8584
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_operator_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Operator CLI for EOS substrate — Operator Interface Layer v1.

Human-driven query + controlled-command surface over linkage_snapshot.
Deterministic. Bounded. No automation.

...

**Lines:** 229 | **Size:** 8,584 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_operator_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_operator_cli-py-_add_common]]`(p) → None`
- **fn** [[scripts-substrate_operator_cli-py-_build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_operator_cli-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate import operator_interface as oi
from eos_ai.substrate import control_bridge as cb
from eos_ai.substrate import control_commands as cc
from eos_ai.substrate import local_executor as lx
```
