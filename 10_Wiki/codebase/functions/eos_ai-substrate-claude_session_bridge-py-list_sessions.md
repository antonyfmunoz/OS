---
type: codebase-function
file: eos_ai/substrate/claude_session_bridge.py
line: 397
generated: 2026-04-12
---

# list_sessions

**File:** [[eos_ai-substrate-claude_session_bridge-py]] | **Line:** 397
**Signature:** `list_sessions(target) → dict[str, Any]`

List tmux sessions visible on this machine.

If target is provided, the payload will include it as metadata and filter
to sessions whose names start with the dex_ prefix. All sessions are
still reported under "all_sessions" for observability.

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-_current_node_id]]
- [[eos_ai-substrate-claude_session_bridge-py-_tmux_list_sessions]]
- [[eos_ai-substrate-claude_session_bridge-py-default_session_target]]
- [[eos_ai-substrate-claude_session_bridge-py-detect_tmux_available]]
