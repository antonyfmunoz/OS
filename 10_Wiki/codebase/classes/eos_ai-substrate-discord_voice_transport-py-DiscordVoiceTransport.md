---
type: codebase-class
file: eos_ai/substrate/discord_voice_transport.py
line: 187
generated: 2026-04-12
---

# DiscordVoiceTransport

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 187

Pure adapter from a Discord voice surface to the bounded voice loop.

Construction is cheap: no network, no event loop, no client. The adapter
is safe to instantiate from any process (operator CLI, smoke test,
`services/discord_bot.py` opt-in hook).

## Methods

- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-__init__]]`() → None` — 
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-_ensure_playback]]`()` — 
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-attach_voice_client]]`(voice_client) → dict[str, Any]` — Attach a real (or fake) Discord VoiceClient to this transport.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-detach_voice_client]]`() → dict[str, Any]` — Drop any attached VoiceClient and return to transcript-only mode.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-set_playback_enabled]]`(enabled) → dict[str, Any]` — Toggle playback on/off without dropping the attached VC.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-play_reply]]`(text) → dict[str, Any]` — Bounded playback entry point for an EOS reply.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-_ensure_node_registered]]`() → None` — Register the discord-side node so VoiceSessionRuntime accepts it.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-start_session]]`(role_slug) → dict[str, Any]` — Start (or resume) a bounded voice session for this transport node.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-end_session]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-inject_utterance]]`(text) → dict[str, Any]` — Bounded entry point. Mirrors transcript_inject.inject_transcript()
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-_latest_agent_reply]]`(session_id) → Optional[str]` — Best-effort: return the most recent AGENT turn text for `session_id`.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-_build_playback_status]]`(mode) → dict[str, Any]` — Build shared PlaybackStatusSnapshot dict for this transport.
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-status_report]]`() → dict[str, Any]` — Bounded snapshot of transport mode + capability + recent events.
