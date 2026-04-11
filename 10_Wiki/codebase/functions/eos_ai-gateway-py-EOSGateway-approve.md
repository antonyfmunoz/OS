---
type: codebase-function
file: eos_ai/gateway.py
line: 1667
generated: 2026-04-11
---

# EOSGateway.approve

**File:** [[eos_ai-gateway-py]] | **Line:** 1667
**Signature:** `approve(approval_id) → dict`

**Class:** [[eos_ai-gateway-py-EOSGateway]]

Move pending → approved, then execute the original request.
Returns the execution result.

## Calls

- [[eos_ai-gateway-py-EOSGateway-_log_gateway_event]]
- [[eos_ai-gateway-py-EOSGateway-_route_agent_task]]
- [[eos_ai-gateway-py-EOSGateway-_route_brief]]
- [[eos_ai-gateway-py-EOSGateway-_route_event]]
- [[eos_ai-gateway-py-EOSGateway-_route_status]]
- [[eos_ai-gateway-py-_utcnow]]

## Called By

- [[services-discord_bot-py-cmd_approve]]
