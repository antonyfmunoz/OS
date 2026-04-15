---
type: codebase-function
file: eos_ai/substrate/remote_identity.py
line: 60
generated: 2026-04-12
---

# validate_command_scope

**File:** [[eos_ai-substrate-remote_identity-py]] | **Line:** 60
**Signature:** `validate_command_scope(command, node_id) → bool`

Confirm a ControlCommand is addressed to this node.

Accepts a ControlCommand or any object with a `.node_id` attribute, or a
dict with a "node_id" key. Returns False on any malformed input — never
raises.
