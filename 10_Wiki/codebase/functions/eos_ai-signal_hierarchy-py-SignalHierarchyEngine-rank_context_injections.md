---
type: codebase-function
file: eos_ai/signal_hierarchy.py
line: 141
generated: 2026-04-11
---

# SignalHierarchyEngine.rank_context_injections

**File:** [[eos_ai-signal_hierarchy-py]] | **Line:** 141
**Signature:** `rank_context_injections(injections, classified_input) → list[dict]`

**Class:** [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine]]

Rank context injections by relevance to classified input.
Higher tier injections come first.
Irrelevant domain injections are filtered out.
