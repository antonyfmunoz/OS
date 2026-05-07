---
type: codebase-function
file: eos_ai/substrate/work_order_dispatch.py
line: 110
generated: 2026-05-07
---

# check_contract_readiness

**File:** [[eos_ai-substrate-work_order_dispatch-py]] | **Line:** 110
**Signature:** `check_contract_readiness() → list[ReadinessCheck]`

Check that work order contracts are importable and functional.

## Calls

- [[eos_ai-substrate-work_order_factory-py-create_google_workspace_discovery_work_order]]
- [[eos_ai-substrate-work_order_factory-py-validate_work_order]]
- [[eos_ai-substrate-work_order_factory-py-work_order_to_bridge_payload]]

## Called By

- [[eos_ai-substrate-work_order_dispatch-py-build_dispatch_package]]
