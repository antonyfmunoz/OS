---
type: codebase-file
path: eos_ai/substrate/claude_responder.py
module: eos_ai.substrate.claude_responder
lines: 179
size: 5310
generated: 2026-04-12
---

# eos_ai/substrate/claude_responder.py

Claude Responder v1 — thin adapter that turns a text prompt into a reply by
routing it through a persistent Claude Code tmux session via
`eos_ai.substrate.claude_session_bridge`.

Purpose
...

**Lines:** 179 | **Size:** 5,310 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[eos_ai-substrate-claude_responder-py-session_name_for_discord_channel]]`(channel_id) → str`
- **fn** [[eos_ai-substrate-claude_responder-py-_empty]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_responder-py-respond_via_claude_session]]`(text) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from eos_ai.substrate import claude_session_bridge as csb
```
