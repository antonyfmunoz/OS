---
type: codebase-class
file: eos_ai/substrate/meeting_transport.py
line: 198
generated: 2026-04-11
---

# MeetingTransport

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 198

Pure adapter from a meeting voice surface to the bounded voice loop.

Construction is cheap: no network, no browser, no client. The adapter is
safe to instantiate from any process (operator CLI, smoke test, future
meeting bridge service).
...

## Methods

- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-__init__]]`() → None` — 
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-attach_playback_sink]]`(sink) → dict[str, Any]` — Attach a bounded playback/egress sink.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-detach_playback_sink]]`() → dict[str, Any]` — Drop any attached sink and return to transcript-only mode.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-attach_source]]`(source) → dict[str, Any]` — Attach a meeting transcript source (duck-typed MeetingSourceProtocol).
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-detach_source]]`(name) → dict[str, Any]` — Detach a previously attached source by name. Never raises.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-list_attached_sources]]`() → list[dict]` — Bounded snapshot of attached sources (excludes the live object).
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-pump_attached_sources]]`() → dict[str, Any]` — Drain up to ``max_per_source`` utterances from each attached source.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-set_playback_enabled]]`(enabled) → dict[str, Any]` — Toggle playback on/off without dropping the attached sink.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-play_reply]]`(text) → dict[str, Any]` — Bounded playback entry point for an EOS reply.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-_record_playback]]`(result) → None` — Bounded in-memory counter for playback observability. Never raises.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-playback_status_snapshot]]`() → dict[str, Any]` — Shared PlaybackStatusSnapshot dict for this meeting transport.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-_ensure_node_registered]]`() → None` — Register the meeting-side node so VoiceSessionRuntime accepts it.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-start_session]]`(role_slug) → dict[str, Any]` — Start (or resume) a bounded voice session for this meeting node.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-end_session]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-inject_utterance]]`(text) → dict[str, Any]` — Bounded entry point. Mirrors transcript_inject.inject_transcript()
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-_latest_agent_reply]]`(session_id) → Optional[str]` — Best-effort: return the most recent AGENT turn text for `session_id`.
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-status_report]]`() → dict[str, Any]` — Bounded snapshot of transport mode + capability + recent events.
