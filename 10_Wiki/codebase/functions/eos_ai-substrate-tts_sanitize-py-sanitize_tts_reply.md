---
type: codebase-function
file: eos_ai/substrate/tts_sanitize.py
line: 92
generated: 2026-04-11
---

# sanitize_tts_reply

**File:** [[eos_ai-substrate-tts_sanitize-py]] | **Line:** 92
**Signature:** `sanitize_tts_reply(text) → str`

Return the clean spoken body of `text`, stripping footer / meta noise.

Contract:
  - Never raises.
  - Always returns a str (possibly empty).
...

## Calls

- [[eos_ai-substrate-tts_sanitize-py-_clip]]

## Called By

- [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-main]]
- [[scripts-substrate_discord_tts_body_only_smoke_test-py-main]]
