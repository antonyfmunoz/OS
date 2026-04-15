---
type: codebase-function
file: eos_ai/substrate/discord_text_transport.py
line: 284
generated: 2026-04-12
---

# ingest_text_message

**File:** [[eos_ai-substrate-discord_text_transport-py]] | **Line:** 284
**Signature:** `ingest_text_message(text) → dict[str, Any]`

Pseudo-live text ingress into the shared voice substrate.

Behavior:
  1. Returns {status: "disabled"} immediately if ingress flag is off.
  2. Returns {status: "gate_denied", detail: <reason>} if any allowlist
...

## Calls

- [[eos_ai-substrate-context_lifecycle-py-_log]]
- [[eos_ai-substrate-discord_text_transport-py-DiscordTextEvent-as_dict]]
- [[eos_ai-substrate-discord_text_transport-py-_TextHistory-record]]
- [[eos_ai-substrate-discord_text_transport-py-_check_gating]]
- [[eos_ai-substrate-discord_text_transport-py-_ingress_enabled]]
- [[eos_ai-substrate-discord_text_transport-py-_log]]
- [[eos_ai-substrate-discord_text_transport-py-_short_preview]]
- [[eos_ai-substrate-resource_guard-py-evaluate_resource_guard]]
- [[eos_ai-substrate-workload_policy-py-classify_workload]]

## Called By

- [[eos_ai-substrate-discord_text_transport-py-maybe_mirror_discord_text_message]]
- [[scripts-substrate_discord_text_tts_smoke_test-py-main]]
