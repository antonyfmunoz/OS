---
type: codebase-function
file: eos_ai/substrate/discord_text_transport.py
line: 757
generated: 2026-04-11
---

# build_tts_reply_envelope

**File:** [[eos_ai-substrate-discord_text_transport-py]] | **Line:** 757
**Signature:** `build_tts_reply_envelope(reply_text) → dict[str, Any]`

Produce a Discord-send envelope for a pseudo-live TTS reply.

Returns a dict with a stable shape:

    {
...

## Calls

- [[eos_ai-substrate-context_lifecycle-py-_log]]
- [[eos_ai-substrate-discord_text_transport-py-_TextHistory-record]]
- [[eos_ai-substrate-discord_text_transport-py-_backend_snapshot]]
- [[eos_ai-substrate-discord_text_transport-py-_ingress_enabled]]
- [[eos_ai-substrate-discord_text_transport-py-_log]]
- [[eos_ai-substrate-discord_text_transport-py-_record_backend]]
- [[eos_ai-substrate-discord_text_transport-py-_reply_max_chars]]
- [[eos_ai-substrate-discord_text_transport-py-_short_preview]]
- [[eos_ai-substrate-discord_text_transport-py-_tts_enabled]]
- [[eos_ai-substrate-discord_text_transport-py-truncate_reply]]

## Called By

- [[eos_ai-substrate-discord_text_transport-py-_claude_responder_ingest]]
- [[eos_ai-substrate-discord_text_transport-py-maybe_mirror_discord_text_message]]
- [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-main]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-main]]
- [[scripts-substrate_discord_tts_body_only_smoke_test-py-main]]
