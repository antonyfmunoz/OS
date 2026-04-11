---
type: codebase-function
file: eos_ai/memory.py
line: 847
generated: 2026-04-11
---

# ConversationMemory.search

**File:** [[eos_ai-memory-py]] | **Line:** 847
**Signature:** `search(query, limit, session_id) → list[Message]`

**Class:** [[eos_ai-memory-py-ConversationMemory]]

Full-text search across all stored messages.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-memory-py-ConversationMemory-_row]]

## Called By

- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-scan_market_signals]]
- [[eos_ai-research_engine-py-ResearchEngine-_parse_model_costs]]
