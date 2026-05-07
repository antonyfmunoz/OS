---
type: codebase-file
path: eos_ai/substrate/windows_desktop_relay_client.py
module: eos_ai.substrate.windows_desktop_relay_client
lines: 355
size: 11374
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/substrate/windows_desktop_relay_client.py

> **ENTRY POINT** — Contains `if __name__` or server start.

WSL-side relay client for the Windows Interactive Desktop Adapter.

Writes action request JSON to the relay inbox and reads result JSON
from the relay outbox. The relay inbox/outbox are shared directories
accessible from both WSL and Windows.
...

**Lines:** 355 | **Size:** 11,374 bytes

## Contains

- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-_resolve_windows_home]]`() → Path | None`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-_default_relay_root]]`() → Path`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-_is_windows_relay_environment]]`() → bool`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-resolve_relay_paths]]`(relay_root) → tuple[Path, Path, Path]`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-write_request_to_relay]]`(request, relay_inbox, dry_run) → Path`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-read_result_from_relay]]`(request_id, relay_outbox, timeout_seconds, poll_interval) → dict[str, Any] | None`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-check_relay_available]]`(relay_inbox, relay_outbox) → dict[str, Any]`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-send_request_and_wait]]`(request, relay_inbox, relay_outbox, timeout_seconds, dry_run) → dict[str, Any]`
- **fn** [[eos_ai-substrate-windows_desktop_relay_client-py-_cli_main]]`() → None`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
```
