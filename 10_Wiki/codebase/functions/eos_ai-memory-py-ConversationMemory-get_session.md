---
type: codebase-function
file: eos_ai/memory.py
line: 746
generated: 2026-05-07
---

# ConversationMemory.get_session

**File:** [[eos_ai-memory-py]] | **Line:** 746
**Signature:** `get_session(session_id, limit) → list[Message]`

**Class:** [[eos_ai-memory-py-ConversationMemory]]

Return all messages in session order.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-memory-py-ConversationMemory-_row]]

## Called By

- [[eos_ai-memory-py-ConversationMemory-format_session_for_prompt]]
