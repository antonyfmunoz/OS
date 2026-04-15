---
type: codebase-file
path: eos_ai/substrate/claude_session_bridge.py
module: eos_ai.substrate.claude_session_bridge
lines: 1149
size: 40395
generated: 2026-04-12
---

# eos_ai/substrate/claude_session_bridge.py

Claude Code Session Bridge v1 — persistent tmux-backed Claude Code sessions.

This module provides an explicit, bounded bridge into persistent Claude Code
CLI sessions running inside tmux. It is designed as a *responder backend*
that later surfaces (Discord text, meeting intelligence, operator interface)
...

**Lines:** 1149 | **Size:** 40,395 bytes

## Used By

- [[eos_ai-substrate-session_watcher-py]]

## Contains

- **class** [[eos_ai-substrate-claude_session_bridge-py-ClaudeSessionTarget]] — 1 methods
- **class** [[eos_ai-substrate-claude_session_bridge-py-ClaudeSessionInfo]] — 1 methods
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_get_session_lock]]`(session_name) → threading.Lock`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-detect_tmux_available]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-detect_claude_cli_available]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-default_session_target]]`() → str`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_current_node_id]]`() → str`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_sanitize_session_name]]`(name) → str`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-make_session_name]]`(kind) → str`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_validate_target]]`(target) → tuple[bool, str]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_validate_session_name]]`(session_name) → tuple[bool, str]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_err]]`(target, session_name, reason) → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_resolve_soul_doc]]`(session_name) → str | None`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_build_claude_launch_cmd]]`(session_name) → tuple[str, str | None]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_run_tmux]]`(args) → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_tmux_has_session]]`(session_name) → bool`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_tmux_list_sessions]]`() → list[dict[str, Any]]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-list_sessions]]`(target) → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-session_status]]`(target, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-ensure_session]]`(target, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-send_message]]`(target, session_name, text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-capture_output]]`(target, session_name) → dict[str, Any]`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_scrub_cli_chrome]]`(text) → str`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_extract_new_reply]]`(before, after) → str`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-_raw_new_region]]`(before_lines, after_text) → str`
- **fn** [[eos_ai-substrate-claude_session_bridge-py-ask_session]]`(target, session_name, text) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
