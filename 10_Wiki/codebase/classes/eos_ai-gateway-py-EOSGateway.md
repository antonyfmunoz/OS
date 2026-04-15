---
type: codebase-class
file: eos_ai/gateway.py
line: 232
generated: 2026-04-12
---

# EOSGateway

**File:** [[eos_ai-gateway-py]] | **Line:** 232

Singleton gateway. EOSGateway() always returns the same instance.
Thread-safe.

## Methods

- [[eos_ai-gateway-py-EOSGateway-__new__]]`() → 'EOSGateway'` — 
- [[eos_ai-gateway-py-EOSGateway-_init_dirs]]`() → None` — 
- [[eos_ai-gateway-py-EOSGateway-_is_memory_query]]`(text) → bool` — 
- [[eos_ai-gateway-py-EOSGateway-_handle_memory_query]]`(text, session_id, cm) → str` — Return memory response string, or '' if query not matched.
- [[eos_ai-gateway-py-EOSGateway-_init_conversation_memory]]`(request) → tuple[object | None, str, str]` — Set up ConversationMemory for this request.
- [[eos_ai-gateway-py-EOSGateway-_handle_automation]]`(request) → dict | None` — Check request prompt against AUTOMATION_TRIGGERS.
- [[eos_ai-gateway-py-EOSGateway-_detect_email_instruction]]`(text) → bool` — 
- [[eos_ai-gateway-py-EOSGateway-_handle_email_instruction]]`(request) → dict | None` — Detect and process founder email folder correction instructions.
- [[eos_ai-gateway-py-EOSGateway-_validate]]`(request) → str | None` — Return an error string if the request is invalid, else None.
- [[eos_ai-gateway-py-EOSGateway-_is_informational]]`(prompt) → bool` — True if the message is purely informational — context, FYI, logging,
- [[eos_ai-gateway-py-EOSGateway-_requires_approval]]`(request) → bool` — Tiered approval gate.
- [[eos_ai-gateway-py-EOSGateway-_log_gateway_event]]`(request, outcome, result_summary) → str` — Log every gateway request to Neon events table.
- [[eos_ai-gateway-py-EOSGateway-handle]]`(request) → dict` — Validate, optionally gate for approval, then route and return result.
- [[eos_ai-gateway-py-EOSGateway-_route_event]]`(request) → dict` — 
- [[eos_ai-gateway-py-EOSGateway-_needs_web_search]]`(text) → bool` — 
- [[eos_ai-gateway-py-EOSGateway-_web_search]]`(query) → str` — 
- [[eos_ai-gateway-py-EOSGateway-_validate_output]]`(output, agent_type, provider) → tuple[str, float, bool]` — Validate agent output quality at gateway boundary.
- [[eos_ai-gateway-py-EOSGateway-_route_to_agent]]`(text, comm_type) → str` — Determine which agent should handle this request.
- [[eos_ai-gateway-py-EOSGateway-_route_agent_task]]`(request, session_id, cm) → dict` — 
- [[eos_ai-gateway-py-EOSGateway-_route_status]]`(request) → dict` — 
- [[eos_ai-gateway-py-EOSGateway-_route_brief]]`(request) → dict` — Notion-first brief: run morning cycle, write to Notion, return URL.
- [[eos_ai-gateway-py-EOSGateway-queue_for_approval]]`(request) → str` — Write request to pending/ directory.
- [[eos_ai-gateway-py-EOSGateway-approve]]`(approval_id) → dict` — Move pending → approved, then execute the original request.
- [[eos_ai-gateway-py-EOSGateway-split_and_order_prompt]]`(text) → list[str]` —         Detect whether a prompt contains multiple distinct instructions and
- [[eos_ai-gateway-py-EOSGateway-handle_ordered]]`(request) → list[dict]` — Split the prompt into ordered parts and process each sequentially.
- [[eos_ai-gateway-py-EOSGateway-classify_intent]]`(text) → str` — Classify a natural language message into one of the known intents.
- [[eos_ai-gateway-py-EOSGateway-get_pending_approvals]]`() → list[dict]` — Return all requests waiting for approval.
