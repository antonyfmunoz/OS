---
type: codebase-function
file: eos_ai/substrate/scene_capabilities.py
line: 123
generated: 2026-04-12
---

# node_supports

**File:** [[eos_ai-substrate-scene_capabilities-py]] | **Line:** 123
**Signature:** `node_supports(node, scene_name) → tuple[bool, set[str]]`

Check whether `node` can satisfy every step of `scene_name`.

For each step, the node must advertise AT LEAST ONE of the acceptable
capability slugs for that step. The daemon and the canonical Capability
enum use different vocabularies, and this is how we bridge them
...

## Calls

- [[eos_ai-substrate-capabilities-py-Capability-all_slugs]]

## Called By

- [[eos_ai-substrate-scene_policy-py-_capability_guarded]]
