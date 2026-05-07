---
type: codebase-function
file: eos_ai/substrate/discord_voice_playback.py
line: 271
generated: 2026-05-07
---

# DiscordVoicePlayback.busy

**File:** [[eos_ai-substrate-discord_voice_playback-py]] | **Line:** 271
**Signature:** `busy() → bool`

**Class:** [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback]]

True if the attached VC is currently playing audio.

Combines our own playback flag with the VC's `is_playing()` if it
exposes one. Defensive against fakes that lack the method.

## Called By

- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-play_text]]
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-snapshot]]
