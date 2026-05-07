---
type: codebase-function
file: eos_ai/substrate/session_watcher.py
line: 629
generated: 2026-05-07
---

# get_watcher

**File:** [[eos_ai-substrate-session_watcher-py]] | **Line:** 629
**Signature:** `get_watcher(session_name) → SessionWatcher | None`

Get the running watcher for a session, if any.

## Called By

- [[eos_ai-substrate-session_discord_bridge-py-PermissionView-allow]]
- [[eos_ai-substrate-session_discord_bridge-py-PermissionView-deny]]
- [[eos_ai-substrate-session_discord_bridge-py-PlanApprovalView-approve]]
- [[eos_ai-substrate-session_discord_bridge-py-PlanApprovalView-reject]]
- [[eos_ai-substrate-session_discord_bridge-py-QuestionOptionView-_make_callback]]
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-handle_answer_command]]
- [[eos_ai-substrate-session_watcher-py-ask_session_watched]]
