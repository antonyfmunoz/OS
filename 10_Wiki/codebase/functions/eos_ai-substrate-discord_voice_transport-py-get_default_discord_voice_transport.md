---
type: codebase-function
file: eos_ai/substrate/discord_voice_transport.py
line: 672
generated: 2026-04-12
---

# get_default_discord_voice_transport

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 672
**Signature:** `get_default_discord_voice_transport() → DiscordVoiceTransport`

Return (or lazily create) a default transport for (guild, channel).

The adapter is intentionally cheap to construct, but operators usually
want one stable instance per voice channel for transport history coherence.

## Called By

- [[eos_ai-substrate-discord_voice_transport-py-maybe_attach_discord_voice_client]]
- [[eos_ai-substrate-discord_voice_transport-py-maybe_mirror_discord_utterance]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-_bootstrap_shared_node]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
