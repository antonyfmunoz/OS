---
type: codebase-function
file: eos_ai/substrate/station_daemon.py
line: 168
generated: 2026-04-12
---

# StationDaemon.run

**File:** [[eos_ai-substrate-station_daemon-py]] | **Line:** 168
**Signature:** `run() → None`

**Class:** [[eos_ai-substrate-station_daemon-py-StationDaemon]]

Blocking main loop. Returns when stop() is called.

## Calls

- [[eos_ai-substrate-station_bus-py-_log]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_emit_heartbeat]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_mark_offline]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_tick]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-register]]
- [[eos_ai-substrate-station_daemon-py-_log]]

## Called By

- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_focus_app]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_play_sound]]
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_speak_text]]
- [[eos_ai-substrate-station_daemon-py-main]]
