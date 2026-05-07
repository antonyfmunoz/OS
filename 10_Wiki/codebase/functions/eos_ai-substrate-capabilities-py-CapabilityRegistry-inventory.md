---
type: codebase-function
file: eos_ai/substrate/capabilities.py
line: 71
generated: 2026-05-07
---

# CapabilityRegistry.inventory

**File:** [[eos_ai-substrate-capabilities-py]] | **Line:** 71
**Signature:** `inventory() → dict[str, list[str]]`

**Class:** [[eos_ai-substrate-capabilities-py-CapabilityRegistry]]

Returns {capability_slug: [node_id, ...]} across all known nodes.
Useful for debug endpoints and future Discord `/substrate` command.
