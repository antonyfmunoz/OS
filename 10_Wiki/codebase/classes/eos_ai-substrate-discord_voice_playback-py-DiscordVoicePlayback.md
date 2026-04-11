---
type: codebase-class
file: eos_ai/substrate/discord_voice_playback.py
line: 227
generated: 2026-04-11
---

# DiscordVoicePlayback

**File:** [[eos_ai-substrate-discord_voice_playback-py]] | **Line:** 227

Bounded playback adapter for ONE attached VoiceClient.

Lifecycle is owned by `DiscordVoiceTransport.attach_voice_client()`. The
transport constructs / discards instances of this class as VoiceClients
come and go. This class never starts background threads or event loops.

## Methods

- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-__init__]]`() → None` — 
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-attach]]`(voice_client) → None` — 
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-detach]]`() → None` — 
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-is_attached]]`() → bool` — 
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-is_enabled]]`() → bool` — 
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-set_enabled]]`(enabled) → None` — 
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-busy]]`() → bool` — True if the attached VC is currently playing audio.
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-play_text]]`(text) → PlaybackResult` — Bounded entry: synthesize `text` and play it on the attached VC.
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-snapshot]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-discord_voice_playback-py-DiscordVoicePlayback-playback_status_snapshot]]`() → dict[str, Any]` — Return the shared PlaybackStatusSnapshot shape as a dict.
