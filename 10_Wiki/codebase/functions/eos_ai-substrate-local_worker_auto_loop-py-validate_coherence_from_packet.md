---
type: codebase-function
file: eos_ai/substrate/local_worker_auto_loop.py
line: 141
generated: 2026-05-07
---

# validate_coherence_from_packet

**File:** [[eos_ai-substrate-local_worker_auto_loop-py]] | **Line:** 141
**Signature:** `validate_coherence_from_packet(packet) → list[str]`

Validate coherence_envelope within a W0 packet.

Lightweight field checks — does not import the full validator
to keep the local worker portable.

## Called By

- [[eos_ai-substrate-local_worker_auto_loop-py-run_auto_loop]]
- [[eos_ai-substrate-local_worker_auto_loop-py-validate_wo_001_packet]]
