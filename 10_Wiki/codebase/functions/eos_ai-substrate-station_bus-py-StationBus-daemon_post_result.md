---
type: codebase-function
file: eos_ai/substrate/station_bus.py
line: 130
generated: 2026-05-07
---

# StationBus.daemon_post_result

**File:** [[eos_ai-substrate-station_bus-py]] | **Line:** 130
**Signature:** `daemon_post_result(node_id, result) → None`

**Class:** [[eos_ai-substrate-station_bus-py-StationBus]]

Post an ActionResult back to EOS.

`kind` is an optional action-kind slug (e.g. "speak_text"). When
provided it is stamped at the top-level of the payload AND mirrored
into `data["kind"]` so older consumers that only read `data` still
...

## Calls

- [[eos_ai-substrate-station_bus-py-StationBus-_inbox_append]]

## Called By

- [[eos_ai-substrate-station_daemon-py-StationDaemon-_post_result]]
- [[scripts-substrate_drainer_smoke_test-py-main]]
- [[scripts-substrate_durable_result_smoke_test-py-main]]
