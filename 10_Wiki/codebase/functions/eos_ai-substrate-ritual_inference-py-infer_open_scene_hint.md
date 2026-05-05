---
type: codebase-function
file: eos_ai/substrate/ritual_inference.py
line: 148
generated: 2026-04-12
---

# infer_open_scene_hint

**File:** [[eos_ai-substrate-ritual_inference-py]] | **Line:** 148
**Signature:** `infer_open_scene_hint(node_id) → InferredHint`

Infer a scene hint for an open_day ritual on `node_id`. Never raises.

Order of signals:
    1. Most recent successful open_scene for this node.
    2. Node metadata preferred_scene / default_scene.
...

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-default]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-ritual_inference-py-_last_successful_scene_for_node]]
- [[eos_ai-substrate-ritual_inference-py-_role_preferred_scene]]

## Called By

- [[eos_ai-substrate-ritual_body-py-run_open_day_body]]
