---
type: codebase-function
file: eos_ai/memory.py
line: 927
generated: 2026-04-12
---

# ConversationMemory.format_channel_history_for_prompt

**File:** [[eos_ai-memory-py]] | **Line:** 927
**Signature:** `format_channel_history_for_prompt(channel, limit, query) → str`

**Class:** [[eos_ai-memory-py-ConversationMemory]]

Format message history for a channel.

When query is provided: fetches top 20 by semantic similarity + last 10
by recency, merges and deduplicates by id, sorts chronologically.
When query is empty: last 40 by recency, reversed to chronological.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
