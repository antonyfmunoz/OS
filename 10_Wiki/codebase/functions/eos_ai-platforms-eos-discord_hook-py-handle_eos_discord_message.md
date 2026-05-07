---
type: codebase-function
file: eos_ai/platforms/eos/discord_hook.py
line: 34
generated: 2026-05-07
---

# handle_eos_discord_message

**File:** [[eos_ai-platforms-eos-discord_hook-py]] | **Line:** 34
**Signature:** `handle_eos_discord_message(text) → str`

Process a founder Discord message through the EOS platform layer.

Returns the formatted response text ready for Discord delivery.
The caller (discord_bot.py) is responsible for sending it.

## Calls

- [[eos_ai-platforms-eos-ea_orchestrator-py-handle_founder_message]]

## Called By

- [[eos_ai-platforms-eos-discord_hook-py-handle_eos_discord_live_message]]
