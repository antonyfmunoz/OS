---
type: codebase-file
path: eos_ai/substrate/local_worker_auto_loop.py
module: eos_ai.substrate.local_worker_auto_loop
lines: 957
size: 35917
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/substrate/local_worker_auto_loop.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Local worker auto-loop for Phase 96.8D (updated 96.8H).

Pull-based local worker that acts as the tmux/GUI relay:
VPS creates governed packet → local worker pulls → local worker
routes GUI actions through Windows Interactive Desktop Adapter →
...

**Lines:** 957 | **Size:** 35,917 bytes

## Contains

- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-load_worker_packet]]`(path) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-validate_wo_001_packet]]`(packet) → list[str]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-validate_execution_binding_from_packet]]`(packet) → list[str]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-validate_coherence_from_packet]]`(packet) → list[str]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-packet_requires_windows_desktop_adapter]]`(packet) → bool`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-check_windows_desktop_adapter_available]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-route_to_windows_desktop_adapter]]`(packet, dry_run) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-write_outbox_message]]`(filename, message) → Path`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-read_inbox_response]]`(filename) → dict[str, Any] | None`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-scan_inbox_for_response]]`(work_order_id) → dict[str, Any] | None`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-build_claimed_status]]`(packet) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-build_preflight_status]]`(packet, checks) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-build_backend_health_status]]`(packet, results) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-build_first_gate_approval_request]]`(packet) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-run_safe_preflight]]`(packet) → list[dict]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-_try_mkdir]]`(path) → bool`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-run_gui_backend_healthcheck]]`() → dict[str, str]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-_extract_decision]]`(response) → str`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-worker_should_wait_for_advisor]]`(response) → bool`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-worker_should_stop]]`(response) → bool`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-_execute_approved_action]]`(packet, response) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-_collect_chrome_process_snapshots]]`() → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-local_worker_auto_loop-py-run_auto_loop]]`(packet_path) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
```
