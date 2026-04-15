---
type: codebase-function
file: services/handlers/intent_handler.py
line: 116
generated: 2026-04-12
---

# run_gateway

**File:** [[services-handlers-intent_handler-py]] | **Line:** 116
**Signature:** `run_gateway(text, channel_name, username, gateway, ki, channel_sessions, default_venture_id, guild_id, channel_id) → str`

Classify intent, build request, call gateway, return output text.
Runs synchronously — called from asyncio executor to avoid blocking.

## Calls

- [[services-handlers-intent_handler-py-build_request]]
