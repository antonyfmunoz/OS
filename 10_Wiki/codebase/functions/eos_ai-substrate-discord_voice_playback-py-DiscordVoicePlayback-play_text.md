---
type: codebase-function
file: eos_ai/substrate/discord_voice_playback.py
line: 293
generated: 2026-05-07
---

# DiscordVoicePlayback.play_text

**File:** [[eos_ai-substrate-discord_voice_playback-py]] | **Line:** 293
**Signature:** `play_text(text) → PlaybackResult`

**Class:** [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback]]

Bounded entry: synthesize `text` and play it on the attached VC.

Returns a PlaybackResult. Never raises. Every result is recorded in
the playback history ring for observability.

## Calls

- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-busy]]
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-is_enabled]]
- [[eos_ai-substrate-discord_voice_playback-py-_PlaybackHistory-record]]
- [[eos_ai-substrate-discord_voice_playback-py-_log]]
- [[eos_ai-substrate-discord_voice_playback-py-_render_tts_to_wav]]
- [[eos_ai-substrate-discord_voice_playback-py-get_playback_history]]

## Called By

- [[scripts-substrate_discord_voice_playback_smoke_test-py-main]]
