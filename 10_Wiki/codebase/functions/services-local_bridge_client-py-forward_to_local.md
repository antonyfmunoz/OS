---
type: codebase-function
file: services/local_bridge_client.py
line: 76
generated: 2026-05-07
---

# forward_to_local

**File:** [[services-local_bridge_client-py]] | **Line:** 76
**Signature:** `forward_to_local(text, session_name) → bool`

Forward a message to the local bridge.

Returns True if successfully forwarded, False otherwise.
Caller should fall back to VPS tmux injection on False.

## Calls

- [[services-local_bridge_client-py-check_health]]
