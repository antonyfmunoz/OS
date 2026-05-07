---
type: codebase-function
file: eos_ai/substrate/discord_voice_transport.py
line: 719
generated: 2026-05-07
---

# maybe_attach_discord_voice_client

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 719
**Signature:** `maybe_attach_discord_voice_client(voice_client) → Optional[dict[str, Any]]`

Opt-in helper for `services/discord_bot.py` to attach a real VC.

Returns None when EOS_DISCORD_VOICE_PLAYBACK_ENABLED is not truthy
(DEFAULT — current bot behavior unchanged). When enabled, attaches
`voice_client` to the default transport for (guild, channel).
...

## Calls

- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-attach_voice_client]]
- [[eos_ai-substrate-discord_voice_transport-py-_log]]
- [[eos_ai-substrate-discord_voice_transport-py-_playback_env_enabled]]
- [[eos_ai-substrate-discord_voice_transport-py-get_default_discord_voice_transport]]

## Called By

- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
