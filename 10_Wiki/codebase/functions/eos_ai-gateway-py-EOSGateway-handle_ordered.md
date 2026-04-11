---
type: codebase-function
file: eos_ai/gateway.py
line: 1741
generated: 2026-04-11
---

# EOSGateway.handle_ordered

**File:** [[eos_ai-gateway-py]] | **Line:** 1741
**Signature:** `handle_ordered(request) → list[dict]`

**Class:** [[eos_ai-gateway-py-EOSGateway]]

Split the prompt into ordered parts and process each sequentially.
Returns a list of result dicts in order.  Single-part prompts return
a one-element list so callers can always iterate uniformly.

## Calls

- [[eos_ai-gateway-py-EOSGateway-handle]]
- [[eos_ai-gateway-py-EOSGateway-split_and_order_prompt]]
