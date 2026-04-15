---
type: codebase-function
file: eos_ai/substrate/discord_mode_routing.py
line: 140
generated: 2026-04-12
---

# resolve_mode_session

**File:** [[eos_ai-substrate-discord_mode_routing-py]] | **Line:** 140
**Signature:** `resolve_mode_session(mode, guild_id, channel_id, metadata) → dict[str, Any]`

Resolve {target, session_name, mode, policy} for a given mode.

Returns a dict:
    {
      "mode":              "builder" | "product" | "unknown",
...

## Calls

- [[eos_ai-substrate-discord_mode_routing-py-_flag_truthy]]
- [[eos_ai-substrate-discord_mode_routing-py-_norm_target]]
