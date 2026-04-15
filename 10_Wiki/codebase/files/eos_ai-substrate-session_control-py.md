---
type: codebase-file
path: eos_ai/substrate/session_control.py
module: eos_ai.substrate.session_control
lines: 260
size: 8103
generated: 2026-04-12
---

# eos_ai/substrate/session_control.py

Session control — lifecycle commands for Claude Code tmux sessions.

Purpose
-------
Provides /clear, /reset, and auto-clear functionality for persistent
...

**Lines:** 260 | **Size:** 8,103 bytes

## Used By

- [[scripts-substrate_mode_behavior_control_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-session_control-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-session_control-py-_auto_clear_threshold]]`() → int`
- **fn** [[eos_ai-substrate-session_control-py-_increment_count]]`(session_name) → int`
- **fn** [[eos_ai-substrate-session_control-py-_reset_count]]`(session_name) → None`
- **fn** [[eos_ai-substrate-session_control-py-get_message_count]]`(session_name) → int`
- **fn** [[eos_ai-substrate-session_control-py-reset_counters_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-session_control-py-clear_session]]`(target, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_control-py-reset_session]]`(target, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_control-py-maybe_auto_clear]]`(session_name) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import sys
import threading
from typing import Any
```
