---
type: codebase-class
file: eos_ai/substrate/node_transport.py
line: 43
generated: 2026-05-07
---

# NodeTransportServer

**File:** [[eos_ai-substrate-node_transport-py]] | **Line:** 43

aiohttp-based HTTP transport for the station daemon.

Created and managed by the StationDaemon. Runs as an asyncio task
alongside the existing synchronous poll loop (which runs in a thread).

...

## Methods

- [[eos_ai-substrate-node_transport-py-NodeTransportServer-__init__]]`(daemon) → None` — 
- [[eos_ai-substrate-node_transport-py-NodeTransportServer-start]]`() → bool` — Start the HTTP transport server. Returns True on success.
- [[eos_ai-substrate-node_transport-py-NodeTransportServer-stop]]`() → None` — Gracefully shut down the HTTP transport.
- [[eos_ai-substrate-node_transport-py-NodeTransportServer-is_running]]`() → bool` — 
- [[eos_ai-substrate-node_transport-py-NodeTransportServer-_handle_health]]`(request) → Any` — Lightweight health check — no auth, no processing.
- [[eos_ai-substrate-node_transport-py-NodeTransportServer-_handle_heartbeat]]`(request) → Any` — Register/refresh daemon heartbeat.
- [[eos_ai-substrate-node_transport-py-NodeTransportServer-_handle_task]]`(request) → Any` — Dispatch a SafeAction and return the result.
- [[eos_ai-substrate-node_transport-py-NodeTransportServer-_handle_status]]`(request) → Any` — Return current node state.
