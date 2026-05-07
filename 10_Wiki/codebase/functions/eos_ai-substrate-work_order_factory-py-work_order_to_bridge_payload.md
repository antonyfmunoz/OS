---
type: codebase-function
file: eos_ai/substrate/work_order_factory.py
line: 175
generated: 2026-05-07
---

# work_order_to_bridge_payload

**File:** [[eos_ai-substrate-work_order_factory-py]] | **Line:** 175
**Signature:** `work_order_to_bridge_payload(wo) → dict`

Convert work order to the JSON payload for POST /work-order.

## Calls

- [[eos_ai-substrate-work_order_contracts-py-WorkOrder-to_dict]]
- [[eos_ai-substrate-work_order_contracts-py-WorkOrderResult-to_dict]]

## Called By

- [[eos_ai-substrate-work_order_dispatch-py-build_dispatch_package]]
- [[eos_ai-substrate-work_order_dispatch-py-check_contract_readiness]]
