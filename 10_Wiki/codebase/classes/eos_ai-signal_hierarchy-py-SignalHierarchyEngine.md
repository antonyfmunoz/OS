---
type: codebase-class
file: eos_ai/signal_hierarchy.py
line: 91
generated: 2026-05-07
---

# SignalHierarchyEngine

**File:** [[eos_ai-signal_hierarchy-py]] | **Line:** 91

*No docstring.*

## Methods

- [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine-__init__]]`(ctx)` — 
- [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine-classify_input]]`(text, channel) → dict` — Classify input signal tier and domain before context injection.
- [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine-_detect_domain]]`(text) → str` — Detect the primary domain from input text.
- [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine-rank_context_injections]]`(injections, classified_input) → list[dict]` — Rank context injections by relevance to classified input.
- [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine-filter_noise]]`(content, min_signal_length) → bool` — Returns True if content has signal, False if it's noise.
- [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine-format_for_prompt]]`(classified_input) → str` — Format signal classification as context for the cognitive loop.
