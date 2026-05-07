---
type: codebase-function
file: eos_ai/signal_hierarchy.py
line: 96
generated: 2026-05-07
---

# SignalHierarchyEngine.classify_input

**File:** [[eos_ai-signal_hierarchy-py]] | **Line:** 96
**Signature:** `classify_input(text, channel) → dict`

**Class:** [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine]]

Classify input signal tier and domain before context injection.
Returns classification dict used downstream by format_for_prompt
and rank_context_injections.

## Calls

- [[eos_ai-signal_hierarchy-py-SignalHierarchyEngine-_detect_domain]]
