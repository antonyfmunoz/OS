---
type: codebase-function
file: eos_ai/substrate/discord_text_transport.py
line: 1124
generated: 2026-04-12
---

# maybe_mirror_discord_text_message

**File:** [[eos_ai-substrate-discord_text_transport-py]] | **Line:** 1124
**Signature:** `maybe_mirror_discord_text_message(text) → Optional[dict[str, Any]]`

Opt-in hook for discord_bot.on_message.

- Returns None immediately if EOS_DISCORD_TEXT_TRANSPORT_ENABLED is not
  truthy. This is the DEFAULT; bot behavior is unchanged.
- Otherwise performs gating + ingress + envelope build, and returns a
...

## Calls

- [[eos_ai-substrate-context_lifecycle-py-_log]]
- [[eos_ai-substrate-context_lifecycle-py-detect_context_pressure]]
- [[eos_ai-substrate-context_lifecycle-py-maybe_clear_and_restore]]
- [[eos_ai-substrate-discord_text_transport-py-DiscordTextEvent-as_dict]]
- [[eos_ai-substrate-discord_text_transport-py-_TextHistory-record]]
- [[eos_ai-substrate-discord_text_transport-py-_check_gating]]
- [[eos_ai-substrate-discord_text_transport-py-_handle_session_command]]
- [[eos_ai-substrate-discord_text_transport-py-_handle_trace_command]]
- [[eos_ai-substrate-discord_text_transport-py-_ingress_enabled]]
- [[eos_ai-substrate-discord_text_transport-py-_log]]
- [[eos_ai-substrate-discord_text_transport-py-_record_backend]]
- [[eos_ai-substrate-discord_text_transport-py-_short_preview]]
- [[eos_ai-substrate-discord_text_transport-py-build_tts_reply_envelope]]
- [[eos_ai-substrate-discord_text_transport-py-ingest_text_message]]

## Called By

- [[scripts-substrate_discord_claude_hardswitch_smoke_test-py-main]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-main]]
- [[scripts-substrate_discord_tts_body_only_smoke_test-py-main]]
