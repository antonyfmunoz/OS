---
type: codebase-function
file: eos_ai/memory.py
line: 912
generated: 2026-04-12
---

# ConversationMemory.format_session_for_prompt

**File:** [[eos_ai-memory-py]] | **Line:** 912
**Signature:** `format_session_for_prompt(session_id, limit) → str`

**Class:** [[eos_ai-memory-py-ConversationMemory]]

Format recent session history for injection into cognitive loop.

## Calls

- [[eos_ai-memory-py-ConversationMemory-get_session]]

## Called By

- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
