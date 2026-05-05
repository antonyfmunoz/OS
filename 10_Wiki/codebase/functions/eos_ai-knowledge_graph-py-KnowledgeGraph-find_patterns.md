---
type: codebase-function
file: eos_ai/knowledge_graph.py
line: 315
generated: 2026-04-12
---

# KnowledgeGraph.find_patterns

**File:** [[eos_ai-knowledge_graph-py]] | **Line:** 315
**Signature:** `find_patterns(venture_id) → list[dict]`

**Class:** [[eos_ai-knowledge_graph-py-KnowledgeGraph]]

Look for recurring patterns in interaction + outcome data.
Returns patterns with confidence scores.
High-confidence patterns are logged as HIGH intelligence signals.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-db-py-resolve_venture]]
