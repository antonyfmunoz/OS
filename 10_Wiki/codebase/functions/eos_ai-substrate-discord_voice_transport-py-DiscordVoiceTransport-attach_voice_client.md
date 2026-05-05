---
type: codebase-function
file: eos_ai/substrate/discord_voice_transport.py
line: 228
generated: 2026-04-12
---

# DiscordVoiceTransport.attach_voice_client

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 228
**Signature:** `attach_voice_client(voice_client) → dict[str, Any]`

**Class:** [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport]]

Attach a real (or fake) Discord VoiceClient to this transport.

Switches the transport mode to ATTACHED and enables bounded
playback by default. Safe to call multiple times — re-attachment
replaces the previous VC.
...

## Calls

- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-_ensure_playback]]
- [[eos_ai-substrate-discord_voice_transport-py-_log]]

## Called By

- [[eos_ai-substrate-discord_voice_transport-py-maybe_attach_discord_voice_client]]
- [[eos_ai-substrate-discord_voice_transport-py-maybe_mirror_discord_utterance]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
