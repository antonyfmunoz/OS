---
type: codebase-function
file: eos_ai/substrate/session_control.py
line: 92
generated: 2026-04-12
---

# clear_session

**File:** [[eos_ai-substrate-session_control-py]] | **Line:** 92
**Signature:** `clear_session(target, session_name) → dict[str, Any]`

Send /clear into a tmux Claude Code session.

This sends the literal "/clear" command to the Claude CLI running in
the tmux session, which clears its conversation context.

## Calls

- [[eos_ai-substrate-session_control-py-_log]]
- [[eos_ai-substrate-session_control-py-_reset_count]]

## Called By

- [[eos_ai-substrate-session_control-py-maybe_auto_clear]]
