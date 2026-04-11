---
type: codebase-function
file: eos_ai/substrate/discord_voice_transport.py
line: 404
generated: 2026-04-11
---

# DiscordVoiceTransport.inject_utterance

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 404
**Signature:** `inject_utterance(text) → dict[str, Any]`

**Class:** [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport]]

Bounded entry point. Mirrors transcript_inject.inject_transcript()
with `source="discord_voice"` and discord-shaped metadata.

Never raises. Always returns a JSON-friendly dict.

## Calls

- [[eos_ai-substrate-discord_voice_transport-py-DiscordTransportEvent-as_dict]]
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-_latest_agent_reply]]
- [[eos_ai-substrate-discord_voice_transport-py-_TransportHistory-record]]
- [[eos_ai-substrate-discord_voice_transport-py-get_transport_history]]

## Called By

- [[eos_ai-substrate-discord_voice_transport-py-maybe_mirror_discord_utterance]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
- [[scripts-substrate_transport_report_smoke_test-py-main]]
