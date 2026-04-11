---
type: codebase-file
path: scripts/substrate_transport_report_cli.py
module: scripts.substrate_transport_report_cli
lines: 150
size: 4677
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_transport_report_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Unified transport report CLI.

Subcommand:
  unified   Print the cross-transport unified report (JSON).

...

**Lines:** 150 | **Size:** 4,677 bytes

## Contains

- **fn** [[scripts-substrate_transport_report_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_transport_report_cli-py-_print_summary]]`(report) → None`
- **fn** [[scripts-substrate_transport_report_cli-py-cmd_unified]]`(args) → int`
- **fn** [[scripts-substrate_transport_report_cli-py-_add_unified_args]]`(p) → None`
- **fn** [[scripts-substrate_transport_report_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_transport_report_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
```
