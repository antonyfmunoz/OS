---
type: codebase-class
file: eos_ai/memory.py
line: 684
generated: 2026-04-12
---

# ConversationMemory

**File:** [[eos_ai-memory-py]] | **Line:** 684

Persistent word-for-word conversation store backed by Neon.

Every message stored. Not summaries. Not truncated.
The complete record — always retrievable, always searchable.

## Methods

- [[eos_ai-memory-py-ConversationMemory-__init__]]`(ctx) → None` — 
- [[eos_ai-memory-py-ConversationMemory-store]]`(session_id, role, content, channel, agent, metadata) → str` — Store a message word for word. Returns message id.
- [[eos_ai-memory-py-ConversationMemory-get_session]]`(session_id, limit) → list[Message]` — Return all messages in session order.
- [[eos_ai-memory-py-ConversationMemory-get_recent]]`(limit, channel) → list[Message]` — Return most recent messages across sessions.
- [[eos_ai-memory-py-ConversationMemory-get_by_position]]`(session_id, position) → _Optional[Message]` — Get message by position in session.
- [[eos_ai-memory-py-ConversationMemory-search]]`(query, limit, session_id) → list[Message]` — Full-text search across all stored messages.
- [[eos_ai-memory-py-ConversationMemory-get_session_summary]]`(session_id) → dict` — Return metadata about a session.
- [[eos_ai-memory-py-ConversationMemory-format_session_for_prompt]]`(session_id, limit) → str` — Format recent session history for injection into cognitive loop.
- [[eos_ai-memory-py-ConversationMemory-format_channel_history_for_prompt]]`(channel, limit, query) → str` — Format message history for a channel.
- [[eos_ai-memory-py-ConversationMemory-_row]]`(row) → Message` — 
