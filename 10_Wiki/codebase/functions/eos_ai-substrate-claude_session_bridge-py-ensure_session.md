---
type: codebase-function
file: eos_ai/substrate/claude_session_bridge.py
line: 489
generated: 2026-04-12
---

# ensure_session

**File:** [[eos_ai-substrate-claude_session_bridge-py]] | **Line:** 489
**Signature:** `ensure_session(target, session_name) → dict[str, Any]`

Ensure a tmux session exists; optionally launch Claude Code inside it.

If the session already exists, this is a no-op and reports created=False.
If tmux is unavailable, degrades safely with ok=True + status=degraded.
If launch_claude is True and the claude CLI is not on PATH, the session
...

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-_build_claude_launch_cmd]]
- [[eos_ai-substrate-claude_session_bridge-py-_current_node_id]]
- [[eos_ai-substrate-claude_session_bridge-py-_err]]
- [[eos_ai-substrate-claude_session_bridge-py-_run_tmux]]
- [[eos_ai-substrate-claude_session_bridge-py-_tmux_has_session]]
- [[eos_ai-substrate-claude_session_bridge-py-_validate_session_name]]
- [[eos_ai-substrate-claude_session_bridge-py-_validate_target]]
- [[eos_ai-substrate-claude_session_bridge-py-detect_claude_cli_available]]
- [[eos_ai-substrate-claude_session_bridge-py-detect_tmux_available]]

## Called By

- [[eos_ai-substrate-claude_session_bridge-py-ask_session]]
