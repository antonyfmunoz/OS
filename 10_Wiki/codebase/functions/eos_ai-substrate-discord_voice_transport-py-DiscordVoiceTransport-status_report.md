---
type: codebase-function
file: eos_ai/substrate/discord_voice_transport.py
line: 566
generated: 2026-04-12
---

# DiscordVoiceTransport.status_report

**File:** [[eos_ai-substrate-discord_voice_transport-py]] | **Line:** 566
**Signature:** `status_report() → dict[str, Any]`

**Class:** [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport]]

Bounded snapshot of transport mode + capability + recent events.

## Calls

- [[eos_ai-substrate-discord_voice_transport-py-DiscordTransportEvent-as_dict]]
- [[eos_ai-substrate-discord_voice_transport-py-DiscordVoiceTransport-_build_playback_status]]
- [[eos_ai-substrate-discord_voice_transport-py-_TransportHistory-latest]]
- [[eos_ai-substrate-discord_voice_transport-py-_env_hook_enabled]]
- [[eos_ai-substrate-discord_voice_transport-py-_log]]
- [[eos_ai-substrate-discord_voice_transport-py-_playback_env_enabled]]
- [[eos_ai-substrate-discord_voice_transport-py-_probe_discord_capability]]
- [[eos_ai-substrate-discord_voice_transport-py-_utcnow_iso]]
- [[eos_ai-substrate-discord_voice_transport-py-get_transport_history]]

## Called By

- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py-main]]
