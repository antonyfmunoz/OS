---
type: codebase-function
file: eos_ai/substrate/scene_policy.py
line: 166
generated: 2026-04-12
---

# select_scene

**File:** [[eos_ai-substrate-scene_policy-py]] | **Line:** 166
**Signature:** `select_scene(node_id, readiness, requested_mode) → SceneDecision`

Deterministic scene selection. Never raises.

`node_id` is accepted for parity with future per-node policy refinement;
it is currently used only for traceability in the reason string.

## Calls

- [[eos_ai-substrate-scene_policy-py-_capability_guarded]]
- [[eos_ai-substrate-scene_policy-py-_normalize_hint]]
- [[eos_ai-substrate-scene_policy-py-_resolve_classification]]
- [[eos_ai-substrate-scenes-py-get_scene]]

## Called By

- [[eos_ai-substrate-ritual_body-py-run_open_day_body]]
