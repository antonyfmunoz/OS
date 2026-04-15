---
type: codebase-file
path: core/environment.py
module: core.environment
lines: 535
size: 19697
generated: 2026-04-12
---

# core/environment.py

environment.py — Execution environment model for the EOS AI OS sandbox layer.

Defines the boundary between PRODUCTION, SANDBOX, and PLAYGROUND modes so
the rest of the system can be told "run against this environment" without
touching module-level constants.
...

**Lines:** 535 | **Size:** 19,697 bytes

## Used By

- [[core-security-environments-py]]
- [[scripts-action_system-py]]
- [[scripts-sandbox_runner-py]]
- [[scripts-sandbox_safety_verifier-py]]
- [[scripts-sandbox_smoke_test-py]]
- [[scripts-workflow_engine-py]]

## Contains

- **class** [[core-environment-py-EnvMode]] — 0 methods
- **class** [[core-environment-py-Environment]] — 22 methods
- **fn** [[core-environment-py-_new_sandbox_name]]`(prefix) → str`
- **fn** [[core-environment-py-make_sandbox]]`() → Environment`
- **fn** [[core-environment-py-make_playground]]`() → Environment`
- **fn** [[core-environment-py-current_environment]]`() → Environment`
- **fn** [[core-environment-py-sandbox_scope]]`() → Iterator[Environment]`

## Import Statements

```python
from __future__ import annotations
import contextlib
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Iterator
```
