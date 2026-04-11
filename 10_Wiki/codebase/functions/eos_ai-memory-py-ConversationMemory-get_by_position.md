---
type: codebase-function
file: eos_ai/memory.py
line: 806
generated: 2026-04-11
---

# ConversationMemory.get_by_position

**File:** [[eos_ai-memory-py]] | **Line:** 806
**Signature:** `get_by_position(session_id, position) → _Optional[Message]`

**Class:** [[eos_ai-memory-py-ConversationMemory]]

Get message by position in session.
position 1 = first message, -1 = last, -2 = two back.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-memory-py-ConversationMemory-_row]]
