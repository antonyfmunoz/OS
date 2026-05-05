---
type: codebase-file
path: eos_ai/substrate/remote_executor.py
module: eos_ai.substrate.remote_executor
lines: 217
size: 8076
generated: 2026-04-12
---

# eos_ai/substrate/remote_executor.py

Control Layer v2 — Remote Executor (daemon-side reader).

A single-threaded loop that drains the existing control_bridge queue for
this node and dispatches each command through the existing local_executor.
The bridge queue remains the ONLY transport. The daemon is just a reader.
...

**Lines:** 217 | **Size:** 8,076 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Used By

- [[scripts-substrate_remote_execution_smoke_test-py]]
- [[scripts-substrate_remote_executor_daemon-py]]

## Contains

- **class** [[eos_ai-substrate-remote_executor-py-RemoteExecutor]] — 5 methods

## Import Statements

```python
from __future__ import annotations
import time
from typing import Any
from eos_ai.substrate import control_bridge as bridge
from eos_ai.substrate import control_commands as cc
from eos_ai.substrate import local_executor
from eos_ai.substrate import remote_identity
```
