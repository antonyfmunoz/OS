---
type: codebase-file
path: core/orchestrator/signals.py
module: core.orchestrator.signals
lines: 209
size: 6341
generated: 2026-04-11
---

# core/orchestrator/signals.py

Signals — filesystem-backed event layer for the orchestrator.

A signal is a named event. Handlers are bound workflow names. When a
signal is emitted, its payload is appended to a pending queue on disk.
The orchestrator loop drains the queue, dispatching each pending
...

**Lines:** 209 | **Size:** 6,341 bytes

## Used By

- [[scripts-emit_signal-py]]
- [[scripts-orchestrator_status-py]]

## Contains

- **class** [[core-orchestrator-signals-py-SignalEmission]] — 1 methods
- **fn** [[core-orchestrator-signals-py-_signal_dir]]`(name) → str`
- **fn** [[core-orchestrator-signals-py-_pending_dir]]`(name) → str`
- **fn** [[core-orchestrator-signals-py-_processed_dir]]`(name) → str`
- **fn** [[core-orchestrator-signals-py-_load_bindings]]`() → dict[str, list[str]]`
- **fn** [[core-orchestrator-signals-py-_save_bindings]]`(bindings) → None`
- **fn** [[core-orchestrator-signals-py-define_signal]]`(name) → None`
- **fn** [[core-orchestrator-signals-py-emit_signal]]`(name, payload) → SignalEmission`
- **fn** [[core-orchestrator-signals-py-register_handler]]`(signal, workflow_name) → None`
- **fn** [[core-orchestrator-signals-py-unregister_handler]]`(signal, workflow_name) → None`
- **fn** [[core-orchestrator-signals-py-get_handlers]]`(signal) → list[str]`
- **fn** [[core-orchestrator-signals-py-list_signals]]`() → list[str]`
- **fn** [[core-orchestrator-signals-py-list_pending]]`(signal) → list[SignalEmission]`
- **fn** [[core-orchestrator-signals-py-mark_processed]]`(emission, outcome) → str`

## Import Statements

```python
from __future__ import annotations
import json
import os
import time
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
```
