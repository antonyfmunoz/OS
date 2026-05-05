---
type: codebase-function
file: eos_ai/substrate/claude_session_bridge.py
line: 894
generated: 2026-04-12
---

# ask_session

**File:** [[eos_ai-substrate-claude_session_bridge-py]] | **Line:** 894
**Signature:** `ask_session(target, session_name, text) → dict[str, Any]`

Ensure → capture-before → send → bounded-poll → capture-after → diff.

Returns a structured dict with best-effort extracted reply text. Never
raises. Degrades safely if tmux/claude CLI are missing.

...

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-_get_session_lock]]
- [[eos_ai-substrate-claude_session_bridge-py-_raw_new_region]]
- [[eos_ai-substrate-claude_session_bridge-py-_scrub_cli_chrome]]
- [[eos_ai-substrate-claude_session_bridge-py-capture_output]]
- [[eos_ai-substrate-claude_session_bridge-py-ensure_session]]
- [[eos_ai-substrate-claude_session_bridge-py-send_message]]
