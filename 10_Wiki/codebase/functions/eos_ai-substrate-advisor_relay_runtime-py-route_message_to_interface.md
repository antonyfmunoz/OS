---
type: codebase-function
file: eos_ai/substrate/advisor_relay_runtime.py
line: 90
generated: 2026-05-07
---

# route_message_to_interface

**File:** [[eos_ai-substrate-advisor_relay_runtime-py]] | **Line:** 90
**Signature:** `route_message_to_interface(message, interface_id) → MessageEnvelope`

Route a message to a specific interface projection.

Returns a new envelope with target set to the interface.
Does not perform transport — caller handles delivery.
