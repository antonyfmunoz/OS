---
type: codebase-class
file: eos_ai/substrate/capabilities.py
line: 52
generated: 2026-04-12
---

# CapabilityRegistry

**File:** [[eos_ai-substrate-capabilities-py]] | **Line:** 52

Query helper over a NodeRegistry.

Kept deliberately thin — no scoring, no preference logic. The capability-
aware router will layer on top of this later; for now it just answers
"which nodes advertise this capability?"

## Methods

- [[eos_ai-substrate-capabilities-py-CapabilityRegistry-__init__]]`(node_registry) → None` — 
- [[eos_ai-substrate-capabilities-py-CapabilityRegistry-nodes_for]]`(capability) → list['Node']` — 
- [[eos_ai-substrate-capabilities-py-CapabilityRegistry-is_available]]`(capability) → bool` — 
- [[eos_ai-substrate-capabilities-py-CapabilityRegistry-inventory]]`() → dict[str, list[str]]` — Returns {capability_slug: [node_id, ...]} across all known nodes.
