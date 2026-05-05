---
type: codebase-function
file: eos_ai/substrate/session_control.py
line: 131
generated: 2026-04-12
---

# reset_session

**File:** [[eos_ai-substrate-session_control-py]] | **Line:** 131
**Signature:** `reset_session(target, session_name) → dict[str, Any]`

Kill and recreate a tmux Claude Code session.

Steps:
1. Kill the existing tmux session (if present)
2. Re-run ensure_session to create a fresh one with Claude launched

## Calls

- [[eos_ai-substrate-session_control-py-_log]]
- [[eos_ai-substrate-session_control-py-_reset_count]]
