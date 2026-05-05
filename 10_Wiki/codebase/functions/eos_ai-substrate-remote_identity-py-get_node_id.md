---
type: codebase-function
file: eos_ai/substrate/remote_identity.py
line: 25
generated: 2026-04-12
---

# get_node_id

**File:** [[eos_ai-substrate-remote_identity-py]] | **Line:** 25
**Signature:** `get_node_id() → str`

Resolve this machine's substrate node id.

Order:
    1. EOS_NODE_ID env var (explicit)
    2. socket.gethostname()
...
