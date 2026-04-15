---
type: codebase-function
file: eos_ai/substrate/session_watcher.py
line: 186
generated: 2026-04-12
---

# SessionWatcher.send_response

**File:** [[eos_ai-substrate-session_watcher-py]] | **Line:** 186
**Signature:** `send_response(text) → dict[str, Any]`

**Class:** [[eos_ai-substrate-session_watcher-py-SessionWatcher]]

Pipe a response back into the tmux session.

## Calls

- [[eos_ai-substrate-claude_session_bridge-py-send_message]]

## Called By

- [[eos_ai-substrate-session_discord_bridge-py-PermissionView-allow]]
- [[eos_ai-substrate-session_discord_bridge-py-PermissionView-deny]]
- [[eos_ai-substrate-session_discord_bridge-py-PlanApprovalView-approve]]
- [[eos_ai-substrate-session_discord_bridge-py-PlanApprovalView-reject]]
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-handle_answer_command]]
