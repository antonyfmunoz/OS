---
type: codebase-function
file: eos_ai/substrate/discord_mode_routing.py
line: 270
generated: 2026-04-11
---

# mode_context

**File:** [[eos_ai-substrate-discord_mode_routing-py]] | **Line:** 270
**Signature:** `mode_context(mode)`

Bind a mode context for the duration of the block.

Unknown/None mode is a no-op — we do not poison the thread-local so the
router keeps its env-default behavior.

## Decorators

- `@contextmanager`
