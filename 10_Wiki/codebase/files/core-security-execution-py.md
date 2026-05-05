---
type: codebase-file
path: core/security/execution.py
module: core.security.execution
lines: 331
size: 11591
generated: 2026-04-12
---

# core/security/execution.py

execution.py — Restricted execution contexts for agent workloads.

Goal
----
When an agent runs code or commands, the security layer should be able
...

**Lines:** 331 | **Size:** 11,591 bytes

## Used By

- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-security-execution-py-ExecutionDenied]] — 0 methods
- **class** [[core-security-execution-py-ExecutionContext]] — 6 methods
- **class** [[core-security-execution-py-ExecutionResult]] — 0 methods
- **class** [[core-security-execution-py-RestrictedExecutor]] — 2 methods
- **fn** [[core-security-execution-py-restricted_context]]`() → Iterator[ExecutionContext]`

## Import Statements

```python
from __future__ import annotations
import os
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Iterator
from typing import Literal
from typing import Sequence
```
