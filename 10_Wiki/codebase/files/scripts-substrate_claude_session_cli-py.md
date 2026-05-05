---
type: codebase-file
path: scripts/substrate_claude_session_cli.py
module: scripts.substrate_claude_session_cli
lines: 171
size: 5362
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_claude_session_cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Claude Code Session Bridge CLI.

Operator-facing wrapper over eos_ai.substrate.claude_session_bridge. Provides
explicit, bounded control over persistent Claude Code tmux sessions on either
the VPS node or the local node.
...

**Lines:** 171 | **Size:** 5,362 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[scripts-substrate_claude_session_cli-py-_print_json]]`(obj) → None`
- **fn** [[scripts-substrate_claude_session_cli-py-cmd_detect]]`(_args) → int`
- **fn** [[scripts-substrate_claude_session_cli-py-cmd_list]]`(args) → int`
- **fn** [[scripts-substrate_claude_session_cli-py-cmd_status]]`(args) → int`
- **fn** [[scripts-substrate_claude_session_cli-py-cmd_ensure]]`(args) → int`
- **fn** [[scripts-substrate_claude_session_cli-py-cmd_send]]`(args) → int`
- **fn** [[scripts-substrate_claude_session_cli-py-cmd_capture]]`(args) → int`
- **fn** [[scripts-substrate_claude_session_cli-py-cmd_ask]]`(args) → int`
- **fn** [[scripts-substrate_claude_session_cli-py-_add_target]]`(p) → None`
- **fn** [[scripts-substrate_claude_session_cli-py-_add_session]]`(p) → None`
- **fn** [[scripts-substrate_claude_session_cli-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from eos_ai.substrate import claude_session_bridge as csb
```
