---
type: codebase-function
file: eos_ai/substrate/discord_voice_playback.py
line: 468
generated: 2026-04-11
---

# DiscordVoicePlayback.playback_status_snapshot

**File:** [[eos_ai-substrate-discord_voice_playback-py]] | **Line:** 468
**Signature:** `playback_status_snapshot() → dict[str, Any]`

**Class:** [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback]]

Return the shared PlaybackStatusSnapshot shape as a dict.

Transport-tagged "discord". Pulls from this adapter's own snapshot
plus an aggregation of the bounded playback history ring filtered
to this adapter's node_id. Never raises.

## Calls

- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-snapshot]]
- [[eos_ai-substrate-discord_voice_playback-py-PlaybackResult-as_dict]]
- [[eos_ai-substrate-discord_voice_playback-py-_PlaybackHistory-latest]]
- [[eos_ai-substrate-discord_voice_playback-py-_log]]
- [[eos_ai-substrate-discord_voice_playback-py-get_playback_history]]

## Called By

- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
