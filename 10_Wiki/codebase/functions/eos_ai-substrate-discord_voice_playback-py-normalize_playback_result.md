---
type: codebase-function
file: eos_ai/substrate/discord_voice_playback.py
line: 564
generated: 2026-04-12
---

# normalize_playback_result

**File:** [[eos_ai-substrate-discord_voice_playback-py]] | **Line:** 564
**Signature:** `normalize_playback_result(raw) → dict[str, Any]`

Coerce any playback result into the canonical envelope.

Canonical shape:
    {
      "transport": "discord" | "meeting" | "<other>",
...

## Calls

- [[eos_ai-substrate-discord_voice_playback-py-PlaybackResult-as_dict]]
- [[eos_ai-substrate-discord_voice_playback-py-_utcnow_iso]]
