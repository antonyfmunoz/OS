---
type: codebase-function
file: eos_ai/substrate/claude_session_bridge.py
line: 585
generated: 2026-04-12
---

# send_message

**File:** [[eos_ai-substrate-claude_session_bridge-py]] | **Line:** 585
**Signature:** `send_message(target, session_name, text) → dict[str, Any]`

Inject text into a tmux session's active pane (followed by Enter).

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-_err]]
- [[eos_ai-substrate-claude_session_bridge-py-_run_tmux]]
- [[eos_ai-substrate-claude_session_bridge-py-_tmux_has_session]]
- [[eos_ai-substrate-claude_session_bridge-py-_validate_session_name]]
- [[eos_ai-substrate-claude_session_bridge-py-_validate_target]]
- [[eos_ai-substrate-claude_session_bridge-py-detect_tmux_available]]

## Called By

- [[eos_ai-substrate-claude_session_bridge-py-ask_session]]
- [[eos_ai-substrate-session_watcher-py-SessionWatcher-send_response]]
- [[eos_ai-substrate-session_watcher-py-ask_session_watched]]
