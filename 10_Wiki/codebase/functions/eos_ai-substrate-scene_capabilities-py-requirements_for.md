---
type: codebase-function
file: eos_ai/substrate/scene_capabilities.py
line: 110
generated: 2026-04-12
---

# requirements_for

**File:** [[eos_ai-substrate-scene_capabilities-py]] | **Line:** 110
**Signature:** `requirements_for(scene_name) → set[str]`

Flat union of every capability slug this scene mentions, across all
accepted vocabularies. Useful for display; NOT the check function.
Unknown scene → empty set.

## Called By

- [[eos_ai-substrate-scene_capabilities-py-scene_requirements_inventory]]
