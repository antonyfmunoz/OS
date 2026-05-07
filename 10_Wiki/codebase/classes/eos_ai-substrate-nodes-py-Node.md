---
type: codebase-class
file: eos_ai/substrate/nodes.py
line: 58
generated: 2026-05-07
---

# Node

**File:** [[eos_ai-substrate-nodes-py]] | **Line:** 58

A single execution target the substrate can reason about.

`capabilities` is a list of capability slugs — kept as plain strings so
this module has no import-cycle with eos_ai.substrate.capabilities.
Callers can validate against `Capability` from that module when needed.

## Methods

- [[eos_ai-substrate-nodes-py-Node-touch]]`() → None` — 
- [[eos_ai-substrate-nodes-py-Node-has_capability]]`(slug) → bool` — 

## Decorators

- `@dataclass`
