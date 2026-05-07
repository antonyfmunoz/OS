---
type: codebase-function
file: eos_ai/substrate/discord_voice_transport.py
line: 277
generated: 2026-05-07
---

# DiscordVoiceTransport.play_reply

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 277
**Signature:** `play_reply(text) → dict[str, Any]`

**Class:** [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport]]

Bounded playback entry point for an EOS reply.

Always returns a JSON-friendly dict. If no VC is attached or
playback is disabled, returns a structured `disabled` result
instead of raising.

## Calls

- [[eos_ai-substrate-discord_voice_transport-py-DiscordTransportEvent-as_dict]]

## Called By

- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
