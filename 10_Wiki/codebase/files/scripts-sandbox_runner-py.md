---
type: codebase-file
path: scripts/sandbox_runner.py
module: scripts.sandbox_runner
lines: 774
size: 26633
tags: [entry-point]
generated: 2026-04-12
---

# scripts/sandbox_runner.py

> **ENTRY POINT** — Contains `if __name__` or server start.

sandbox_runner.py — Safe experimentation surface for the EOS AI OS.

The sandbox runner is the operator-facing CLI for the sandbox layer.
Every command here runs against an isolated environment (sandbox or
playground), never against production. The runner is the *only*
...

**Lines:** 774 | **Size:** 26,633 bytes

## Depends On

- [[core-environment-py]]

## Contains

- **fn** [[scripts-sandbox_runner-py-_dumps]]`(obj) → str`
- **fn** [[scripts-sandbox_runner-py-_banner]]`(env) → None`
- **fn** [[scripts-sandbox_runner-py-_resolve_env]]`(args) → Environment`
- **fn** [[scripts-sandbox_runner-py-_list_sandboxes]]`() → list[dict[str, Any]]`
- **fn** [[scripts-sandbox_runner-py-_dir_size_mb]]`(path) → float`
- **fn** [[scripts-sandbox_runner-py-_parse_marker]]`(path) → dict[str, str]`
- **fn** [[scripts-sandbox_runner-py-_load_sandbox_by_name]]`(name) → Environment | None`
- **fn** [[scripts-sandbox_runner-py-_diff_workspace]]`(env) → dict[str, Any]`
- **fn** [[scripts-sandbox_runner-py-_cmd_run_workflow]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_run_action]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_orchestrator_tick]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_playground]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_replay]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_stage]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_list]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_diff]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_clean]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_cmd_inspect]]`(args) → int`
- **fn** [[scripts-sandbox_runner-py-_add_env_flags]]`(p) → None`
- **fn** [[scripts-sandbox_runner-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from core.environment import Environment
from core.environment import EnvMode
from core.environment import PLAYGROUND_ROOT
from core.environment import SANDBOX_ROOT
from core.environment import make_playground
from core.environment import make_sandbox
```
