---
type: codebase-class
file: eos_ai/context_compaction.py
line: 27
generated: 2026-04-11
---

# ContextCompactor

**File:** [[eos_ai-context_compaction-py]] | **Line:** 27

*No docstring.*

## Methods

- [[eos_ai-context_compaction-py-ContextCompactor-__init__]]`(ctx)` — 
- [[eos_ai-context_compaction-py-ContextCompactor-_ensure_table]]`() → None` — 
- [[eos_ai-context_compaction-py-ContextCompactor-estimate_tokens]]`(messages) → int` — Rough estimate: 4 chars per token.
- [[eos_ai-context_compaction-py-ContextCompactor-should_compact]]`(messages) → bool` — 
- [[eos_ai-context_compaction-py-ContextCompactor-compact]]`(messages, session_id) → dict` — Compress a message list into a structured brief.
- [[eos_ai-context_compaction-py-ContextCompactor-build_seeded_context]]`(brief) → str` — Format a compaction brief as a system prompt prefix.
- [[eos_ai-context_compaction-py-ContextCompactor-get_lineage]]`(session_id) → list[dict]` — Return all compaction records for a session in chronological order.
