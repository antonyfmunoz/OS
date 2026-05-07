---
type: codebase-file
path: eos_ai/substrate/control_commands.py
module: eos_ai.substrate.control_commands
lines: 104
size: 3668
generated: 2026-05-07
---

# eos_ai/substrate/control_commands.py

Control Layer v1 — Command Envelope.

Defines ControlCommand: the deterministic, JSON-serializable unit of work
that flows VPS (brain) → Control Bridge → Local Agent (hands).

...

**Lines:** 104 | **Size:** 3,668 bytes

## Used By

- [[eos_ai-substrate-execution_adapter-py]]

## Contains

- **class** [[eos_ai-substrate-control_commands-py-ControlCommand]] — 2 methods
- **fn** [[eos_ai-substrate-control_commands-py-make_command]]`(action, payload) → ControlCommand`
- **fn** [[eos_ai-substrate-control_commands-py-validate]]`(cmd) → tuple[bool, str]`

## Import Statements

```python
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from typing import Any
from typing import Optional
```
