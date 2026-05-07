---
type: codebase-class
file: eos_ai/substrate/nodes.py
line: 83
generated: 2026-05-07
---

# NodeRegistry

**File:** [[eos_ai-substrate-nodes-py]] | **Line:** 83

Persistent node registry.

State is held in memory for fast access and flushed through
eos_ai.substrate.storage on every upsert/remove, so nodes survive across
processes. Storage falls back to a JSON file if Neon is unavailable.

## Methods

- [[eos_ai-substrate-nodes-py-NodeRegistry-__init__]]`() → None` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-_load]]`() → None` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-_flush]]`() → None` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-upsert]]`(node) → Node` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]`(node_id) → Optional[Node]` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-remove]]`(node_id) → None` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-all]]`() → list[Node]` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-by_type]]`(node_type) → list[Node]` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-with_capability]]`(slug) → list[Node]` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-online]]`() → list[Node]` — 
- [[eos_ai-substrate-nodes-py-NodeRegistry-purge_stale]]`() → list[str]` — Remove nodes whose last_seen is older than max_age_hours.
- [[eos_ai-substrate-nodes-py-NodeRegistry-default]]`() → 'NodeRegistry'` — Process-wide default registry, seeded with the current VPS as the
- [[eos_ai-substrate-nodes-py-NodeRegistry-reset_default_for_tests]]`() → None` — 
