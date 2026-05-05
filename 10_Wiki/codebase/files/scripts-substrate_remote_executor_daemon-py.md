---
type: codebase-file
path: scripts/substrate_remote_executor_daemon.py
module: scripts.substrate_remote_executor_daemon
lines: 92
size: 2665
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_remote_executor_daemon.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Control Layer v2 — Remote Executor Daemon CLI.

Subcommands:
    run       --node NODE_ID [--interval 1.0] [--batch 5]
    run-once  --node NODE_ID
...

**Lines:** 92 | **Size:** 2,665 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-remote_executor-py]]

## Contains

- **fn** [[scripts-substrate_remote_executor_daemon-py-_emit]]`(payload) → int`
- **fn** [[scripts-substrate_remote_executor_daemon-py-_cmd_run]]`(args) → int`
- **fn** [[scripts-substrate_remote_executor_daemon-py-_cmd_run_once]]`(args) → int`
- **fn** [[scripts-substrate_remote_executor_daemon-py-_cmd_status]]`(args) → int`
- **fn** [[scripts-substrate_remote_executor_daemon-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate.remote_executor import RemoteExecutor
from eos_ai.substrate import remote_identity
```
