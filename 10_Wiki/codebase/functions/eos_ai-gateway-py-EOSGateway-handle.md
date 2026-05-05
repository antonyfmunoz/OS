---
type: codebase-function
file: eos_ai/gateway.py
line: 610
generated: 2026-04-12
---

# EOSGateway.handle

**File:** [[eos_ai-gateway-py]] | **Line:** 610
**Signature:** `handle(request) → dict`

**Class:** [[eos_ai-gateway-py-EOSGateway]]

Validate, optionally gate for approval, then route and return result.

Returns a dict with at minimum:
    {"status": "ok"|"error"|"pending", ...result fields}

## Calls

- [[eos_ai-gateway-py-EOSGateway-_handle_automation]]
- [[eos_ai-gateway-py-EOSGateway-_handle_email_instruction]]
- [[eos_ai-gateway-py-EOSGateway-_handle_memory_query]]
- [[eos_ai-gateway-py-EOSGateway-_init_conversation_memory]]
- [[eos_ai-gateway-py-EOSGateway-_is_memory_query]]
- [[eos_ai-gateway-py-EOSGateway-_log_gateway_event]]
- [[eos_ai-gateway-py-EOSGateway-_requires_approval]]
- [[eos_ai-gateway-py-EOSGateway-_route_agent_task]]
- [[eos_ai-gateway-py-EOSGateway-_route_brief]]
- [[eos_ai-gateway-py-EOSGateway-_route_event]]
- [[eos_ai-gateway-py-EOSGateway-_route_status]]
- [[eos_ai-gateway-py-EOSGateway-_validate]]
- [[eos_ai-gateway-py-EOSGateway-queue_for_approval]]

## Called By

- [[eos_ai-gateway-py-EOSGateway-handle_ordered]]
- [[services-discord_bot-py-_listen_loop]]
- [[services-discord_bot-py-end_active_meeting]]
- [[services-discord_bot-py-handle_meeting_voice]]
