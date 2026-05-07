---
type: codebase-file
path: scripts/orchestrator.py
module: scripts.orchestrator
lines: 1122
size: 45647
tags: [entry-point]
generated: 2026-05-07
---

# scripts/orchestrator.py

> **ENTRY POINT** — Contains `if __name__` or server start.

orchestrator.py — Continuous, autonomous execution layer for EOS.

Sits above the workflow engine and turns it from an on-demand runner into a
self-driving system. Four internal agents cooperate:

...

**Lines:** 1122 | **Size:** 45,647 bytes

## Depends On

- [[scripts-workflow_engine-py]]

## Used By

- [[core-control_plane-py]]

## Contains

- **class** [[scripts-orchestrator-py-TriggerType]] — 0 methods
- **class** [[scripts-orchestrator-py-JobStatus]] — 0 methods
- **class** [[scripts-orchestrator-py-Job]] — 2 methods
- **class** [[scripts-orchestrator-py-Verifier]] — 2 methods
- **class** [[scripts-orchestrator-py-ActivityLog]] — 3 methods
- **class** [[scripts-orchestrator-py-ExecutionQueue]] — 9 methods
- **class** [[scripts-orchestrator-py-SchedulerAgent]] — 5 methods
- **class** [[scripts-orchestrator-py-EventAgent]] — 7 methods
- **class** [[scripts-orchestrator-py-RetryPolicy]] — 2 methods
- **class** [[scripts-orchestrator-py-Orchestrator]] — 11 methods
- **fn** [[scripts-orchestrator-py-_parse_hhmm]]`(s) → dtime`
- **fn** [[scripts-orchestrator-py-_graph_freshness_ok]]`() → bool`
- **fn** [[scripts-orchestrator-py-build_default_jobs]]`() → list[Job]`
- **fn** [[scripts-orchestrator-py-_install_signal_handlers]]`(orch) → None`
- **fn** [[scripts-orchestrator-py-_cmd_list]]`(args) → int`
- **fn** [[scripts-orchestrator-py-_cmd_status]]`(args) → int`
- **fn** [[scripts-orchestrator-py-_cmd_trigger]]`(args) → int`
- **fn** [[scripts-orchestrator-py-_cmd_start]]`(args) → int`
- **fn** [[scripts-orchestrator-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import signal
import sys
import threading
import time
import traceback
import uuid
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import time as dtime
from datetime import timezone
from enum import Enum
from pathlib import Path
from queue import Empty
from queue import Full
from queue import Queue
from typing import Any
from typing import Callable
from scripts.workflow_engine import Workflow
from scripts.workflow_engine import WorkflowEngine
from scripts.workflow_engine import build_content_workflow
from scripts.workflow_engine import build_refactor_workflow
from scripts.workflow_engine import build_research_workflow
```
