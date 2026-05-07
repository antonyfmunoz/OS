---
type: codebase-function
file: eos_ai/platforms/eos/discord_hook.py
line: 133
generated: 2026-05-07
---

# handle_eos_discord_live_message

**File:** [[eos_ai-platforms-eos-discord_hook-py]] | **Line:** 133
**Signature:** `handle_eos_discord_live_message(text) → str`

Process a founder Discord message through the EA live runtime.

Unlike handle_eos_discord_message (which uses the EA orchestrator directly),
this routes through the live runtime for control phrase interception,
immediate execution, and live session binding.
...

## Calls

- [[eos_ai-platforms-eos-discord_hook-py-_log]]
- [[eos_ai-platforms-eos-discord_hook-py-handle_eos_discord_message]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_log]]
