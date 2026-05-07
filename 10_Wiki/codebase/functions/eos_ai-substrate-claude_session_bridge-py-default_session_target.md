---
type: codebase-function
file: eos_ai/substrate/claude_session_bridge.py
line: 172
generated: 2026-05-07
---

# default_session_target

**File:** [[eos_ai-substrate-claude_session_bridge-py]] | **Line:** 172
**Signature:** `default_session_target() → str`

Pick a default target based on EOS_NODE_ROLE / hostname.

Convention:
  - EOS_NODE_ROLE=vps   -> "vps"
  - EOS_NODE_ROLE=local -> "local"
...

## Called By

- [[eos_ai-substrate-claude_session_bridge-py-list_sessions]]
