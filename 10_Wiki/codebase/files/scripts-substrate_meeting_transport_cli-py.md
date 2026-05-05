---
type: codebase-file
path: scripts/substrate_meeting_transport_cli.py
module: scripts.substrate_meeting_transport_cli
lines: 266
size: 8192
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_meeting_transport_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Meeting voice transport CLI.

Subcommands:
  status   Print MeetingTransport.status_report() (JSON).
  start    Start a bounded voice session for the meeting node.
...

**Lines:** 266 | **Size:** 8,192 bytes

## Contains

- **fn** [[scripts-substrate_meeting_transport_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_meeting_transport_cli-py-_transport]]`(args)`
- **fn** [[scripts-substrate_meeting_transport_cli-py-cmd_status]]`(args) → int`
- **fn** [[scripts-substrate_meeting_transport_cli-py-cmd_start]]`(args) → int`
- **fn** [[scripts-substrate_meeting_transport_cli-py-cmd_inject]]`(args) → int`
- **fn** [[scripts-substrate_meeting_transport_cli-py-cmd_end]]`(args) → int`
- **fn** [[scripts-substrate_meeting_transport_cli-py-_add_common]]`(p) → None`
- **fn** [[scripts-substrate_meeting_transport_cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[scripts-substrate_meeting_transport_cli-py-_run_source_ops]]`(args) → None`
- **fn** [[scripts-substrate_meeting_transport_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
```
