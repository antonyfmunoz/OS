---
type: codebase-file
path: core/control_plane.py
module: core.control_plane
lines: 322
size: 10798
tags: [entry-point]
generated: 2026-04-12
---

# core/control_plane.py

> **ENTRY POINT** — Contains `if __name__` or server start.

control_plane.py — Unified control plane composing the orchestrator with
persistent agents.

Design:
  * We do NOT modify scripts/orchestrator.py. Instead, ControlPlane wraps
...

**Lines:** 322 | **Size:** 10,798 bytes

## Depends On

- [[core-persistent_agents-py]]
- [[scripts-orchestrator-py]]

## Contains

- **class** [[core-control_plane-py-ControlPlaneState]] — 0 methods
- **class** [[core-control_plane-py-ControlPlane]] — 10 methods
- **fn** [[core-control_plane-py-_log]]`(event) → None`
- **fn** [[core-control_plane-py-_cmd_start]]`(args) → int`
- **fn** [[core-control_plane-py-_cmd_status]]`(args) → int`
- **fn** [[core-control_plane-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import signal
import sys
import threading
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from core.persistent_agents import PersistentAgent
from core.persistent_agents import default_agents
from scripts.orchestrator import Orchestrator
from scripts.orchestrator import build_default_jobs
from scripts.orchestrator import _install_signal_handlers
```
