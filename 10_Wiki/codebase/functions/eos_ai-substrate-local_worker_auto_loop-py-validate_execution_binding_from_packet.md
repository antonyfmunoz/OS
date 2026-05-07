---
type: codebase-function
file: eos_ai/substrate/local_worker_auto_loop.py
line: 93
generated: 2026-05-07
---

# validate_execution_binding_from_packet

**File:** [[eos_ai-substrate-local_worker_auto_loop-py]] | **Line:** 93
**Signature:** `validate_execution_binding_from_packet(packet) → list[str]`

Validate execution_binding within a W0 packet.

Checks that the binding exists and all 6 layers are present.
Does not import the full validator to avoid circular deps at
runtime on the local worker — uses lightweight field checks.

## Called By

- [[eos_ai-substrate-local_worker_auto_loop-py-validate_wo_001_packet]]
