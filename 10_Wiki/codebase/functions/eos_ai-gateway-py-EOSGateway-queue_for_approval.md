---
type: codebase-function
file: eos_ai/gateway.py
line: 1650
generated: 2026-04-12
---

# EOSGateway.queue_for_approval

**File:** [[eos_ai-gateway-py]] | **Line:** 1650
**Signature:** `queue_for_approval(request) → str`

**Class:** [[eos_ai-gateway-py-EOSGateway]]

Write request to pending/ directory.
Returns approval_id (timestamp-based, human-readable).

## Calls

- [[eos_ai-gateway-py-_timestamp_id]]
- [[eos_ai-gateway-py-_utcnow]]

## Called By

- [[eos_ai-gateway-py-EOSGateway-handle]]
