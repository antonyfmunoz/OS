---
type: codebase-file
path: scripts/substrate_router_claude_runtime_activation_smoke_test.py
module: scripts.substrate_router_claude_runtime_activation_smoke_test
lines: 186
size: 7127
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_router_claude_runtime_activation_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Regression smoke test: router claude_cli backend runtime activation.

Locks in the invariants behind the 2026-04-08 fix where the os-discord
container wasn't reaching the host tmux session. Verifies:

...

**Lines:** 186 | **Size:** 7,127 bytes

## Contains

- **fn** [[scripts-substrate_router_claude_runtime_activation_smoke_test-py-_reload_router]]`()`
- **fn** [[scripts-substrate_router_claude_runtime_activation_smoke_test-py-_install_bridge_stub]]`()`
- **fn** [[scripts-substrate_router_claude_runtime_activation_smoke_test-py-_stub_registry_providers]]`(mr_mod)`
- **fn** [[scripts-substrate_router_claude_runtime_activation_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_router_claude_runtime_activation_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import logging
import os
import sys
```
