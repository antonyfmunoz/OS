---
type: codebase-class
file: eos_ai/substrate/station_bus.py
line: 70
generated: 2026-04-12
---

# StationBus

**File:** [[eos_ai-substrate-station_bus-py]] | **Line:** 70

Process-wide station transport hub.

The bus is intentionally stateless across restarts — all state lives in
the outbox/inbox files. This keeps the VPS side idempotent: a restart
of EOS cannot lose pending actions, and a restart of the daemon cannot
...

## Methods

- [[eos_ai-substrate-station_bus-py-StationBus-__init__]]`(root) → None` — 
- [[eos_ai-substrate-station_bus-py-StationBus-_outbox]]`(node_id) → Path` — 
- [[eos_ai-substrate-station_bus-py-StationBus-_inbox]]`(node_id) → Path` — 
- [[eos_ai-substrate-station_bus-py-StationBus-dispatch]]`(node_id, action) → None` — Append a SafeAction to the node's outbox.
- [[eos_ai-substrate-station_bus-py-StationBus-pending_outbox]]`(node_id) → list[dict]` — 
- [[eos_ai-substrate-station_bus-py-StationBus-drain_inbox]]`(node_id) → list[dict]` — Read and clear the node's inbox, returning everything the daemon
- [[eos_ai-substrate-station_bus-py-StationBus-daemon_take_outbox]]`(node_id) → list[dict]` — Daemon-side: read and clear the outbox in one atomic swap.
- [[eos_ai-substrate-station_bus-py-StationBus-daemon_post_result]]`(node_id, result) → None` — Post an ActionResult back to EOS.
- [[eos_ai-substrate-station_bus-py-StationBus-daemon_post_event]]`(node_id, event) → None` — 
- [[eos_ai-substrate-station_bus-py-StationBus-_inbox_append]]`(node_id, msg) → None` — 
