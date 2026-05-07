---
type: codebase-file
path: scripts/substrate_router_claude_primary_smoke_test.py
module: scripts.substrate_router_claude_primary_smoke_test
lines: 236
size: 7955
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_router_claude_primary_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Router Claude-CLI Primary Backend — smoke test.

Proves the broader router (eos_ai.model_router.call_with_fallback) now:

  1. Tries Claude CLI (persistent tmux session) FIRST when available.
...

**Lines:** 236 | **Size:** 7,955 bytes

## Depends On

- [[eos_ai-accountability-py]]
- [[eos_ai-model_router-py]]

## Contains

- **class** [[scripts-substrate_router_claude_primary_smoke_test-py-_FakeClaudeResponder]] — 2 methods
- **class** [[scripts-substrate_router_claude_primary_smoke_test-py-_CCSDKTripwire]] — 1 methods
- **class** [[scripts-substrate_router_claude_primary_smoke_test-py-_CCSDKFake]] — 2 methods
- **fn** [[scripts-substrate_router_claude_primary_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_router_claude_primary_smoke_test-py-_install_claude_responder]]`(fake) → None`
- **fn** [[scripts-substrate_router_claude_primary_smoke_test-py-_install_cc_sdk]]`(fn) → None`
- **fn** [[scripts-substrate_router_claude_primary_smoke_test-py-_force_router_availability]]`() → None`
- **fn** [[scripts-substrate_router_claude_primary_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import sys
from eos_ai import model_router as mr
from eos_ai.model_router import ModelProvider
from eos_ai.model_router import PROVIDER_PRIORITY
from eos_ai.model_router import PROVIDER_PRIORITY_FAST
from eos_ai.model_router import RoutingResult
from eos_ai.model_router import call_with_fallback
from eos_ai.model_router import get_router
```
