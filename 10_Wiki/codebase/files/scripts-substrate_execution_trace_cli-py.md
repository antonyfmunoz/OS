---
type: codebase-file
path: scripts/substrate_execution_trace_cli.py
module: scripts.substrate_execution_trace_cli
lines: 178
size: 5371
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_execution_trace_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Operator CLI for EOS execution trace history.

Usage:
    python3 scripts/substrate_execution_trace_cli.py latest
    python3 scripts/substrate_execution_trace_cli.py show --trace-id abc12345
...

**Lines:** 178 | **Size:** 5,371 bytes

## Contains

- **fn** [[scripts-substrate_execution_trace_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_execution_trace_cli-py-_history]]`()`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_latest]]`(args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_show]]`(args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_by_mode]]`(args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_by_session]]`(args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_compact]]`(args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_clear_history]]`(_args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_by_provider]]`(args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_by_path]]`(args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-cmd_summary]]`(_args) → int`
- **fn** [[scripts-substrate_execution_trace_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_execution_trace_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter
```
