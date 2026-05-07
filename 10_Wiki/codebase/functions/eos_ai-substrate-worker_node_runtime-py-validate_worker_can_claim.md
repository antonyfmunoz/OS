---
type: codebase-function
file: eos_ai/substrate/worker_node_runtime.py
line: 36
generated: 2026-05-07
---

# validate_worker_can_claim

**File:** [[eos_ai-substrate-worker_node_runtime-py]] | **Line:** 36
**Signature:** `validate_worker_can_claim(work_order, worker_profile) → tuple[bool, str]`

Check if a worker can claim a work order based on capabilities.

## Calls

- [[eos_ai-substrate-worker_node_contracts-py-WorkerProfile-supports_capability]]
- [[eos_ai-substrate-worker_node_runtime-py-_infer_required_capabilities]]
