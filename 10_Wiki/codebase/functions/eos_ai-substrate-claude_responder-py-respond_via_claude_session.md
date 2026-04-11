---
type: codebase-function
file: eos_ai/substrate/claude_responder.py
line: 72
generated: 2026-04-11
---

# respond_via_claude_session

**File:** [[eos_ai-substrate-claude_responder-py]] | **Line:** 72
**Signature:** `respond_via_claude_session(text) → dict[str, Any]`

Route `text` into a persistent Claude Code tmux session and return reply.

Flow:
  1. Validate input; empty text → ok=False (empty_text).
  2. Check tmux + claude CLI availability; degrade safely if missing.
...

## Calls

- [[eos_ai-substrate-claude_responder-py-_empty]]
