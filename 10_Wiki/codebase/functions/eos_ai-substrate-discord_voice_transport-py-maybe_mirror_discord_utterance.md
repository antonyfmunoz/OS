---
type: codebase-function
file: eos_ai/substrate/discord_voice_transport.py
line: 750
generated: 2026-04-11
---

# maybe_mirror_discord_utterance

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 750
**Signature:** `maybe_mirror_discord_utterance(text) → Optional[dict[str, Any]]`

Opt-in mirror hook for `services/discord_bot.py`.

Behavior:
  - Returns `None` immediately if EOS_DISCORD_VOICE_TRANSPORT_ENABLED is
    not truthy. This is the DEFAULT — existing Discord behavior unchanged.
...

## Calls

- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-attach_voice_client]]
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-inject_utterance]]
- [[eos_ai-substrate-discord_voice_transport-py-_env_hook_enabled]]
- [[eos_ai-substrate-discord_voice_transport-py-_log]]
- [[eos_ai-substrate-discord_voice_transport-py-_playback_env_enabled]]
- [[eos_ai-substrate-discord_voice_transport-py-get_default_discord_voice_transport]]

## Called By

- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
