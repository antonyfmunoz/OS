---
type: codebase-file
path: scripts/action_system.py
module: scripts.action_system
lines: 1241
size: 49015
tags: [entry-point]
generated: 2026-04-12
---

# scripts/action_system.py

> **ENTRY POINT** — Contains `if __name__` or server start.

action_system.py — Controlled execution layer on top of the EOS cognition stack.

Sits between the AI (which proposes actions) and the filesystem / shell
(which executes them). Every action goes through the same pipeline:

...

**Lines:** 1241 | **Size:** 49,015 bytes

## Depends On

- [[core-capability-py]]
- [[core-environment-py]]
- [[scripts-query_graph-py]]

## Used By

- [[scripts-sandbox_safety_verifier-py]]
- [[scripts-sandbox_smoke_test-py]]

## Contains

- **class** [[scripts-action_system-py-ActionType]] — 0 methods
- **class** [[scripts-action_system-py-RiskLevel]] — 1 methods
- **class** [[scripts-action_system-py-ActionStatus]] — 0 methods
- **class** [[scripts-action_system-py-Impact]] — 0 methods
- **class** [[scripts-action_system-py-Action]] — 0 methods
- **class** [[scripts-action_system-py-ActionResult]] — 0 methods
- **class** [[scripts-action_system-py-ActionSystem]] — 25 methods
- **fn** [[scripts-action_system-py-_new_id]]`() → str`
- **fn** [[scripts-action_system-py-_short_hash]]`(s) → str`
- **fn** [[scripts-action_system-py-_abs]]`(target) → Path`
- **fn** [[scripts-action_system-py-_rel_to_root]]`(target) → str`
- **fn** [[scripts-action_system-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
from scripts.query_graph import GraphQuery
from core.environment import Environment
from core.capability import OperationKind
from core.capability import operation_for_action_type
```
