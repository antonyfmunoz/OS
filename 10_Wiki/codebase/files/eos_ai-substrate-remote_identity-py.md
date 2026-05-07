---
type: codebase-file
path: eos_ai/substrate/remote_identity.py
module: eos_ai.substrate.remote_identity
lines: 81
size: 2411
generated: 2026-05-07
---

# eos_ai/substrate/remote_identity.py

Control Layer v2 — Remote Identity (lightweight).

Deterministic node identity + scope matching for the remote executor daemon.
NO crypto. NO networking. Just env/hostname lookups and a string compare.

...

**Lines:** 81 | **Size:** 2,411 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[eos_ai-substrate-remote_identity-py-get_node_id]]`() → str`
- **fn** [[eos_ai-substrate-remote_identity-py-get_node_token]]`() → str`
- **fn** [[eos_ai-substrate-remote_identity-py-validate_command_scope]]`(command, node_id) → bool`

## Import Statements

```python
from __future__ import annotations
import os
import socket
from typing import Any
from eos_ai.substrate import control_commands as cc
```
