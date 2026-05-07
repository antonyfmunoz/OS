---
type: codebase-class
file: eos_ai/substrate/station_daemon.py
line: 101
generated: 2026-05-07
---

# StationDaemon

**File:** [[eos_ai-substrate-station_daemon-py]] | **Line:** 101

Minimal local node process.

Responsibilities:
  1. Register itself into NodeRegistry on start.
  2. Poll StationBus outbox on `poll_interval_s`.
...

## Methods

- [[eos_ai-substrate-station_daemon-py-StationDaemon-__init__]]`(node_id) → None` — 
- [[eos_ai-substrate-station_daemon-py-StationDaemon-register]]`() → Node` — Upsert this node into NodeRegistry so EOS can see it as alive.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-stop]]`() → None` — 
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_start_http_transport]]`() → None` — Start the aiohttp HTTP transport in a background thread (best-effort).
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_http_wait_loop]]`(loop) → None` — Wait in the async loop until the daemon's stop event is set.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_stop_http_transport]]`() → None` — Stop the HTTP transport (best-effort).
- [[eos_ai-substrate-station_daemon-py-StationDaemon-run]]`() → None` — Blocking main loop. Returns when stop() is called.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_tick]]`() → None` — 
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_process_action]]`(raw) → Optional[_HandlerOutcome]` — Process a single action dict and return the outcome.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_play_sound]]`(action) → _HandlerOutcome` — PLAY_SOUND — attempt a local sound playback via a portable CLI tool.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_speak_text]]`(action) → _HandlerOutcome` — SPEAK_TEXT — attempt local TTS via a portable CLI tool.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_open_url]]`(action) → _HandlerOutcome` — OPEN_URL — open an http(s) URL using the stdlib `webbrowser` module.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_launch_app]]`(action) → _HandlerOutcome` — LAUNCH_APP — start a process from the app allow-list.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_open_scene]]`(action) → _HandlerOutcome` — OPEN_SCENE — expand a code-declared scene into its safe steps and
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_handle_focus_app]]`(action) → _HandlerOutcome` — FOCUS_APP — raise a window belonging to an allow-listed app.
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_detect_audio_player]]`() → Optional[str]` — 
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_detect_tts]]`() → Optional[str]` — 
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_post_result]]`(action_id, outcome) → None` — 
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_emit_heartbeat]]`() → None` — 
- [[eos_ai-substrate-station_daemon-py-StationDaemon-_mark_offline]]`() → None` — 
