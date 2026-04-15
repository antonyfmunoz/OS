---
type: codebase-file
path: scripts/watch_graph.py
module: scripts.watch_graph
lines: 527
size: 17341
tags: [entry-point]
generated: 2026-04-12
---

# scripts/watch_graph.py

> **ENTRY POINT** — Contains `if __name__` or server start.

watch_graph.py — Near real-time file watcher for the codebase graph.

Watches SCAN_DIRS (eos_ai, services, scripts, core) via watchdog/inotify and
triggers incremental graph updates as files are edited, created, or deleted.
Keeps the cognition stack fresh without manual rebuilds or git-hook latency.
...

**Lines:** 527 | **Size:** 17,341 bytes

## Depends On

- [[scripts-incremental_graph-py]]

## Contains

- **class** [[scripts-watch_graph-py-CodebaseEventHandler]] — 7 methods
- **fn** [[scripts-watch_graph-py-_now]]`() → str`
- **fn** [[scripts-watch_graph-py-_is_tracked_path]]`(abs_path) → bool`
- **fn** [[scripts-watch_graph-py-_append_perf]]`(record) → None`
- **fn** [[scripts-watch_graph-py-_run_overlay_chain]]`(verbose) → None`
- **fn** [[scripts-watch_graph-py-_process_batch]]`(paths) → None`
- **fn** [[scripts-watch_graph-py-_debounce_loop]]`(handler, pending, lock, cond, stop_flag) → None`
- **fn** [[scripts-watch_graph-py-watch]]`() → int`
- **fn** [[scripts-watch_graph-py-once]]`(paths) → int`
- **fn** [[scripts-watch_graph-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Iterable
from scripts.incremental_graph import NON_PYTHON_EXTENSIONS
from scripts.incremental_graph import ROOT
from scripts.incremental_graph import SCAN_DIRS
from scripts.incremental_graph import SKIP_DIRS
from scripts.incremental_graph import SKIP_FILES
from scripts.incremental_graph import update as incremental_update
```
