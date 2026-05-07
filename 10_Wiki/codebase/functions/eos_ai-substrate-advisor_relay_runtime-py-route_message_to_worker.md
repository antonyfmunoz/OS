---
type: codebase-function
file: eos_ai/substrate/advisor_relay_runtime.py
line: 120
generated: 2026-05-07
---

# route_message_to_worker

**File:** [[eos_ai-substrate-advisor_relay_runtime-py]] | **Line:** 120
**Signature:** `route_message_to_worker(message, worker_id) → MessageEnvelope`

Route a message to a specific worker node.

Returns a new envelope with target set to the worker.
Does not perform transport — caller handles delivery.
