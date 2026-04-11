---
type: codebase-function
file: eos_ai/substrate/discord_mode_routing.py
line: 113
generated: 2026-04-11
---

# resolve_discord_mode

**File:** [[eos_ai-substrate-discord_mode_routing-py]] | **Line:** 113
**Signature:** `resolve_discord_mode(guild_id, channel_id) → str`

Classify a Discord (guild, channel) into a substrate mode.

Returns one of: "builder" | "product" | "unknown".

Exact-match allowlists only. Builder wins if a channel appears in
...

## Calls

- [[eos_ai-substrate-discord_mode_routing-py-_parse_id_set]]
