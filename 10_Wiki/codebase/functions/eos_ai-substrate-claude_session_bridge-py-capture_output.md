---
type: codebase-function
file: eos_ai/substrate/claude_session_bridge.py
line: 649
generated: 2026-04-12
---

# capture_output

**File:** [[eos_ai-substrate-claude_session_bridge-py]] | **Line:** 649
**Signature:** `capture_output(target, session_name) → dict[str, Any]`

Capture bounded pane output from a tmux session.

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-_err]]
- [[eos_ai-substrate-claude_session_bridge-py-_run_tmux]]
- [[eos_ai-substrate-claude_session_bridge-py-_tmux_has_session]]
- [[eos_ai-substrate-claude_session_bridge-py-_validate_session_name]]
- [[eos_ai-substrate-claude_session_bridge-py-_validate_target]]
- [[eos_ai-substrate-claude_session_bridge-py-detect_tmux_available]]

## Called By

- [[eos_ai-substrate-claude_session_bridge-py-ask_session]]
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-_poll_once]]
