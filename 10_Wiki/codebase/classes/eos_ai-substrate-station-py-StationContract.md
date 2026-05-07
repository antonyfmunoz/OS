---
type: codebase-class
file: eos_ai/substrate/station.py
line: 113
generated: 2026-05-07
---

# StationContract

**File:** [[eos_ai-substrate-station-py]] | **Line:** 113

EOS-side handle for one local station.

Holds the most recent heartbeat, tracks in-flight actions, and accepts
inbound events. This is a pure in-memory contract object — transport
(WebSocket, etc.) is out of scope for the bridging branch.
...

## Methods

- [[eos_ai-substrate-station-py-StationContract-__init__]]`(node_id) → None` — 
- [[eos_ai-substrate-station-py-StationContract-record_heartbeat]]`(hb) → None` — 
- [[eos_ai-substrate-station-py-StationContract-record_event]]`(evt) → None` — 
- [[eos_ai-substrate-station-py-StationContract-record_result]]`(result) → None` — 
- [[eos_ai-substrate-station-py-StationContract-propose]]`(action) → SafeAction` — Register an action for transmission to the station.
- [[eos_ai-substrate-station-py-StationContract-inflight]]`() → list[SafeAction]` — 
- [[eos_ai-substrate-station-py-StationContract-event_log]]`() → list[StationEvent]` — 
- [[eos_ai-substrate-station-py-StationContract-result_for]]`(action_id) → Optional[ActionResult]` — 
