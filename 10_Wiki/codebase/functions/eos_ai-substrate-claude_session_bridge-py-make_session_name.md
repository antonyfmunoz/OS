---
type: codebase-function
file: eos_ai/substrate/claude_session_bridge.py
line: 214
generated: 2026-04-12
---

# make_session_name

**File:** [[eos_ai-substrate-claude_session_bridge-py]] | **Line:** 214
**Signature:** `make_session_name(kind) → str`

Build a stable, tmux-safe session name.

Examples:
  make_session_name("main")                  -> "dex_main"
  make_session_name("discord", "123", "456") -> "dex_discord_123_456"
...

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-_sanitize_session_name]]
